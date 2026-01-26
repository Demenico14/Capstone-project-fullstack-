#!/usr/bin/env python3
"""
Chart Generation Utilities for CropIoT Analytics
Creates charts and visualizations for sensor data and analytics
"""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import base64
from io import BytesIO
from typing import Dict, List, Optional, Tuple

class ChartGenerator:
    """Generates charts for sensor data and analytics"""
    
    def __init__(self, analytics_engine):
        self.analytics = analytics_engine
        self.chart_colors = {
            'soil_moisture': '#3498db',    # Blue
            'ph': '#e74c3c',               # Red
            'temperature': '#f39c12',      # Orange
            'humidity': '#2ecc71'          # Green
        }
        
        # Set up matplotlib style
        plt.style.use('default')
        plt.rcParams['figure.figsize'] = (12, 6)
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.alpha'] = 0.3
    
    def create_trend_chart(self, sensor_id: str, days: int = 7) -> str:
        """Create a trend chart for a specific sensor over the last N days"""
        df = self.analytics.load_data()
        if df.empty:
            return self._create_no_data_chart("No data available")
        
        # Filter data for the sensor and time period
        cutoff_date = datetime.now() - timedelta(days=days)
        sensor_data = df[
            (df['sensor_id'] == sensor_id) & 
            (df['timestamp'] >= cutoff_date)
        ].copy()
        
        if sensor_data.empty:
            return self._create_no_data_chart(f"No data for {sensor_id}")
        
        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Sensor Trends - {sensor_id} (Last {days} days)', fontsize=16, fontweight='bold')
        
        metrics = ['soil_moisture', 'ph', 'temperature', 'humidity']
        titles = ['Soil Moisture (%)', 'pH Level', 'Temperature (°C)', 'Humidity (%)']
        
        for i, (metric, title) in enumerate(zip(metrics, titles)):
            ax = axes[i // 2, i % 2]
            
            # Filter out NaN values
            metric_data = sensor_data[['timestamp', metric]].dropna()
            
            if not metric_data.empty:
                ax.plot(metric_data['timestamp'], metric_data[metric], 
                       color=self.chart_colors[metric], linewidth=2, marker='o', markersize=4)
                
                # Add optimal range shading if available
                if metric in self.analytics.optimal_ranges:
                    optimal = self.analytics.optimal_ranges[metric]
                    ax.axhspan(optimal['min'], optimal['max'], alpha=0.2, color='green', label='Optimal Range')
                
                # Format x-axis
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
                
                # Add current value annotation
                if len(metric_data) > 0:
                    last_value = metric_data[metric].iloc[-1]
                    ax.annotate(f'Current: {last_value:.1f}', 
                              xy=(metric_data['timestamp'].iloc[-1], last_value),
                              xytext=(10, 10), textcoords='offset points',
                              bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                              fontsize=9)
            else:
                ax.text(0.5, 0.5, 'No data available', ha='center', va='center', 
                       transform=ax.transAxes, fontsize=12)
            
            ax.set_title(title, fontweight='bold')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def create_daily_averages_chart(self, sensor_id: str, days: int = 14) -> str:
        """Create a chart showing daily averages for a sensor"""
        daily_averages = self.analytics.calculate_daily_averages(days)
        
        if sensor_id not in daily_averages or not daily_averages[sensor_id]:
            return self._create_no_data_chart(f"No daily averages for {sensor_id}")
        
        data = daily_averages[sensor_id]
        dates = list(data.keys())
        dates.sort()
        
        # Prepare data for plotting
        plot_data = {metric: [] for metric in ['soil_moisture', 'ph', 'temperature', 'humidity']}
        date_objects = []
        
        for date_str in dates:
            date_objects.append(datetime.strptime(date_str, '%Y-%m-%d'))
            for metric in plot_data.keys():
                value = data[date_str][metric]
                plot_data[metric].append(value if value is not None else np.nan)
        
        # Create chart
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Daily Averages - {sensor_id} (Last {days} days)', fontsize=16, fontweight='bold')
        
        metrics = ['soil_moisture', 'ph', 'temperature', 'humidity']
        titles = ['Soil Moisture (%)', 'pH Level', 'Temperature (°C)', 'Humidity (%)']
        
        for i, (metric, title) in enumerate(zip(metrics, titles)):
            ax = axes[i // 2, i % 2]
            
            # Plot data
            valid_data = [(date, val) for date, val in zip(date_objects, plot_data[metric]) if not np.isnan(val)]
            
            if valid_data:
                dates_valid, values_valid = zip(*valid_data)
                ax.bar(dates_valid, values_valid, color=self.chart_colors[metric], alpha=0.7, width=0.8)
                
                # Add optimal range line if available
                if metric in self.analytics.optimal_ranges:
                    optimal = self.analytics.optimal_ranges[metric]
                    ax.axhline(y=optimal['min'], color='green', linestyle='--', alpha=0.7, label='Min Optimal')
                    ax.axhline(y=optimal['max'], color='green', linestyle='--', alpha=0.7, label='Max Optimal')
                
                # Format x-axis
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            else:
                ax.text(0.5, 0.5, 'No data available', ha='center', va='center', 
                       transform=ax.transAxes, fontsize=12)
            
            ax.set_title(title, fontweight='bold')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def create_yield_score_chart(self, yield_data: Dict) -> str:
        """Create a chart showing yield scores for all sensors"""
        if not yield_data:
            return self._create_no_data_chart("No yield data available")
        
        sensors = list(yield_data.keys())
        scores = [yield_data[sensor]['score'] for sensor in sensors]
        grades = [yield_data[sensor]['grade'] for sensor in sensors]
        
        # Create chart
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle('Yield Estimation Summary', fontsize=16, fontweight='bold')
        
        # Bar chart of scores
        colors = ['#2ecc71' if score >= 80 else '#f39c12' if score >= 60 else '#e74c3c' for score in scores]
        bars = ax1.bar(sensors, scores, color=colors, alpha=0.8)
        
        # Add score labels on bars
        for bar, score in zip(bars, scores):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{score:.1f}', ha='center', va='bottom', fontweight='bold')
        
        ax1.set_title('Yield Scores by Sensor', fontweight='bold')
        ax1.set_ylabel('Yield Score (0-100)')
        ax1.set_ylim(0, 105)
        ax1.grid(True, alpha=0.3)
        
        # Add grade zones
        ax1.axhspan(90, 100, alpha=0.1, color='green', label='A Grade (90-100)')
        ax1.axhspan(80, 90, alpha=0.1, color='lightgreen', label='B Grade (80-89)')
        ax1.axhspan(70, 80, alpha=0.1, color='yellow', label='C Grade (70-79)')
        ax1.axhspan(60, 70, alpha=0.1, color='orange', label='D Grade (60-69)')
        ax1.axhspan(0, 60, alpha=0.1, color='red', label='F Grade (0-59)')
        
        # Pie chart of grade distribution
        grade_counts = {}
        for grade in grades:
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        if grade_counts:
            grade_colors = {'A': '#2ecc71', 'B': '#27ae60', 'C': '#f39c12', 'D': '#e67e22', 'F': '#e74c3c'}
            pie_colors = [grade_colors.get(grade, '#95a5a6') for grade in grade_counts.keys()]
            
            ax2.pie(grade_counts.values(), labels=grade_counts.keys(), colors=pie_colors, 
                   autopct='%1.0f%%', startangle=90)
            ax2.set_title('Grade Distribution', fontweight='bold')
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def create_comparison_chart(self, metric: str, days: int = 7) -> str:
        """Create a comparison chart showing all sensors for a specific metric"""
        df = self.analytics.load_data()
        if df.empty:
            return self._create_no_data_chart("No data available")
        
        # Filter data for the time period
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_data = df[df['timestamp'] >= cutoff_date].copy()
        
        if recent_data.empty:
            return self._create_no_data_chart(f"No recent data for {metric}")
        
        # Create chart
        fig, ax = plt.subplots(figsize=(15, 8))
        
        sensors = recent_data['sensor_id'].unique()
        
        for sensor in sensors:
            sensor_data = recent_data[recent_data['sensor_id'] == sensor]
            metric_data = sensor_data[['timestamp', metric]].dropna()
            
            if not metric_data.empty:
                ax.plot(metric_data['timestamp'], metric_data[metric], 
                       label=sensor, linewidth=2, marker='o', markersize=4)
        
        # Add optimal range if available
        if metric in self.analytics.optimal_ranges:
            optimal = self.analytics.optimal_ranges[metric]
            ax.axhspan(optimal['min'], optimal['max'], alpha=0.2, color='green', label='Optimal Range')
        
        # Format chart
        metric_titles = {
            'soil_moisture': 'Soil Moisture (%)',
            'ph': 'pH Level',
            'temperature': 'Temperature (°C)',
            'humidity': 'Humidity (%)'
        }
        
        ax.set_title(f'{metric_titles.get(metric, metric)} - All Sensors Comparison (Last {days} days)', 
                    fontsize=14, fontweight='bold')
        ax.set_ylabel(metric_titles.get(metric, metric))
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _create_no_data_chart(self, message: str) -> str:
        """Create a simple chart showing no data message"""
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, message, ha='center', va='center', 
               transform=ax.transAxes, fontsize=16, 
               bbox=dict(boxstyle='round,pad=1', facecolor='lightgray', alpha=0.8))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string for web display"""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close(fig)  # Important: close figure to free memory
        return f"data:image/png;base64,{image_base64}"
    
    def save_chart_to_file(self, chart_base64: str, filename: str, directory: str = "static/charts"):
        """Save base64 chart to file"""
        os.makedirs(directory, exist_ok=True)
        
        # Remove the data URL prefix
        image_data = chart_base64.split(',')[1]
        
        filepath = os.path.join(directory, filename)
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(image_data))
        
        return filepath

# Utility functions for easy chart generation
def generate_all_charts(analytics_engine, yield_estimator, output_dir: str = "static/charts"):
    """Generate all charts and save them to files"""
    chart_gen = ChartGenerator(analytics_engine)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    charts = {}
    
    # Get all sensors
    df = analytics_engine.load_data()
    if not df.empty:
        sensors = df['sensor_id'].unique()
        
        # Generate trend charts for each sensor
        for sensor in sensors:
            chart_base64 = chart_gen.create_trend_chart(sensor, days=7)
            filename = f"trend_{sensor.lower()}.png"
            filepath = chart_gen.save_chart_to_file(chart_base64, filename, output_dir)
            charts[f"trend_{sensor}"] = {
                'base64': chart_base64,
                'file': filepath,
                'title': f'Trends - {sensor}'
            }
            
            # Generate daily averages chart
            chart_base64 = chart_gen.create_daily_averages_chart(sensor, days=14)
            filename = f"daily_{sensor.lower()}.png"
            filepath = chart_gen.save_chart_to_file(chart_base64, filename, output_dir)
            charts[f"daily_{sensor}"] = {
                'base64': chart_base64,
                'file': filepath,
                'title': f'Daily Averages - {sensor}'
            }
        
        # Generate comparison charts for each metric
        for metric in ['soil_moisture', 'ph', 'temperature', 'humidity']:
            chart_base64 = chart_gen.create_comparison_chart(metric, days=7)
            filename = f"comparison_{metric}.png"
            filepath = chart_gen.save_chart_to_file(chart_base64, filename, output_dir)
            charts[f"comparison_{metric}"] = {
                'base64': chart_base64,
                'file': filepath,
                'title': f'All Sensors - {metric.replace("_", " ").title()}'
            }
    
    # Generate yield score chart
    yield_data = yield_estimator.get_all_sensor_yields()
    if yield_data:
        chart_base64 = chart_gen.create_yield_score_chart(yield_data)
        filename = "yield_scores.png"
        filepath = chart_gen.save_chart_to_file(chart_base64, filename, output_dir)
        charts['yield_scores'] = {
            'base64': chart_base64,
            'file': filepath,
            'title': 'Yield Score Summary'
        }
    
    return charts
