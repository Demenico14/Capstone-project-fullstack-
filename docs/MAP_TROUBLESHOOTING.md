# Farm Map Troubleshooting Guide

## Map Not Showing?

If you don't see the farm map, follow these steps:

### 1. Check Environment Variables

Make sure your `.env.local` file has the correct coordinates:

\`\`\`bash
# Node Coordinates (latitude,longitude)
NEXT_PUBLIC_NODE_COORDINATES={"Sensor_1":"-17.8252,31.0335","Sensor_2":"-17.8255,31.0340","Sensor_3":"-17.8248,31.0345"}

# Farm Center Coordinates
NEXT_PUBLIC_FARM_CENTER_LAT=-17.8252
NEXT_PUBLIC_FARM_CENTER_LNG=31.0335
\`\`\`

**Important:** After changing `.env.local`, you MUST restart the Next.js dev server:
\`\`\`bash
# Stop the server (Ctrl+C) and restart:
npm run dev
\`\`\`

### 2. Verify Package Installation

Make sure you have the required packages installed:

\`\`\`bash
npm install leaflet react-leaflet
npm install -D @types/leaflet
\`\`\`

### 3. Check Browser Console

Open your browser's Developer Tools (F12) and check the Console tab for errors:

- Look for `[v0]` prefixed messages to see debug info
- Check for any red error messages
- Verify that coordinates are being parsed correctly

### 4. Common Issues

#### Issue: "window is not defined" or SSR errors
**Solution:** The map component uses dynamic imports to avoid SSR issues. Make sure you're using the latest version of the component.

#### Issue: Map shows but no markers
**Solution:** 
- Check that `NEXT_PUBLIC_NODE_COORDINATES` is valid JSON
- Verify sensor IDs in the coordinates match your actual sensor IDs (e.g., "Sensor_1", not "sensor_1")
- Check browser console for coordinate parsing errors

#### Issue: Map tiles not loading
**Solution:**
- Check your internet connection (map tiles come from OpenStreetMap)
- Try a different tile provider by modifying the TileLayer URL in `farm-map.tsx`

#### Issue: Markers in wrong location
**Solution:**
- Verify your coordinates are in the correct format: `latitude,longitude`
- Make sure latitude comes first (negative for southern hemisphere)
- Example for Zimbabwe: `-17.8252,31.0335` (lat is negative, lng is positive)

### 5. Debug Mode

The map component includes debug logging. Check your browser console for messages like:

\`\`\`
[v0] FarmMap mounted, readings: 3
[v0] Node coordinates string: {"Sensor_1":"-17.8252,31.0335",...}
[v0] Parsed coordinate for Sensor_1: {lat: -17.8252, lng: 31.0335}
[v0] Map center: {lat: "-17.8252", lng: "31.0335"}
\`\`\`

If you don't see these messages, the component might not be rendering.

### 6. Test Your Coordinates

You can verify your coordinates are correct by:

1. Go to [Google Maps](https://maps.google.com)
2. Right-click on your farm location
3. Click "What's here?"
4. Copy the coordinates (format: `latitude, longitude`)
5. Update your `.env.local` file

### 7. Still Not Working?

If the map still doesn't show:

1. Clear your browser cache (Ctrl+Shift+Delete)
2. Restart the Next.js dev server
3. Try a different browser
4. Check that port 3000 is not blocked by firewall
5. Verify you're accessing the "Farm Map" tab in the dashboard

### 8. Alternative: Simple Coordinate View

If you need a quick solution without the full map, you can use the simple coordinate-based visualization by checking the browser console for coordinate data and verifying sensors are being detected.

## Need More Help?

Check the browser console for detailed error messages and coordinate parsing information. All debug messages are prefixed with `[v0]` for easy filtering.
