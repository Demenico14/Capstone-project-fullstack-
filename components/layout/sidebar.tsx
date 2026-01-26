"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import {
  Home,
  History,
  Settings,
  Sprout,
  Activity,
  Database,
  Moon,
  Sun,
  TrendingUp,
  ChevronLeft,
  ChevronRight,
  Droplets,
  Microscope,
  LogOut,
  User,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useState, useEffect } from "react"

interface SidebarProps {
  isCollapsed: boolean
  setIsCollapsed: (collapsed: boolean) => void
  user?: { name: string; email: string } | null
  onClose?: () => void
  isMobile?: boolean
}

export function Sidebar({ isCollapsed, setIsCollapsed, user, onClose, isMobile }: SidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [isDark, setIsDark] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  useEffect(() => {
    const isDarkMode = document.documentElement.classList.contains("dark")
    setIsDark(isDarkMode)
  }, [])

  const toggleDarkMode = () => {
    document.documentElement.classList.toggle("dark")
    setIsDark(!isDark)
  }

  const toggleSidebar = () => {
    setIsCollapsed(!isCollapsed)
  }

  const handleLogout = async () => {
    setIsLoggingOut(true)
    try {
      await fetch("/api/auth/logout", { method: "POST" })
      router.push("/login")
      router.refresh()
    } catch (error) {
      console.error("Logout error:", error)
    } finally {
      setIsLoggingOut(false)
    }
  }

  const navItems = [
    { href: "/", label: "Dashboard", icon: Home },
    { href: "/yield-prediction", label: "Yield Prediction", icon: TrendingUp },
    { href: "/disease-detection", label: "Disease Detection", icon: Microscope },
    { href: "/water-balance", label: "Water Balance", icon: Droplets },
    { href: "/history", label: "History", icon: History },
    { href: "/settings", label: "Settings", icon: Settings },
  ]

  const collapsed = isMobile ? false : isCollapsed

  return (
    <aside
      className={cn(
        "h-screen border-r border-sidebar-border bg-sidebar transition-all duration-300 ease-in-out flex flex-col",
        isMobile ? "w-full" : collapsed ? "fixed left-0 top-0 z-40 w-20" : "fixed left-0 top-0 z-40 w-64",
      )}
    >
      <div className="flex h-full flex-col">
        {/* Header */}
        <div className="flex h-16 items-center justify-between border-b border-sidebar-border px-4">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary">
              <Sprout className="h-6 w-6 text-primary-foreground" />
            </div>
            {!collapsed && (
              <div className="flex flex-col">
                <span className="font-bold text-lg text-sidebar-foreground whitespace-nowrap">CropIoT</span>
                <span className="text-xs text-muted-foreground whitespace-nowrap">Admin Panel</span>
              </div>
            )}
          </div>
          {isMobile ? (
            <button
              onClick={onClose}
              className="shrink-0 rounded-lg p-1.5 hover:bg-sidebar-accent transition-all duration-200"
              aria-label="Close menu"
            >
              <X className="h-5 w-5 text-sidebar-foreground" />
            </button>
          ) : (
            <>
              {!collapsed && (
                <button
                  onClick={toggleSidebar}
                  className="shrink-0 rounded-lg p-1.5 hover:bg-sidebar-accent transition-all duration-200"
                  aria-label="Collapse sidebar"
                >
                  <ChevronLeft className="h-5 w-5 text-sidebar-foreground" />
                </button>
              )}
              {collapsed && (
                <button
                  onClick={toggleSidebar}
                  className="absolute right-2 top-5 shrink-0 rounded-lg p-1.5 hover:bg-sidebar-accent transition-all duration-200"
                  aria-label="Expand sidebar"
                >
                  <ChevronRight className="h-4 w-4 text-sidebar-foreground" />
                </button>
              )}
            </>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-4 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-all duration-200 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground relative group",
                  isActive ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-sm" : "text-sidebar-foreground",
                  collapsed && !isMobile && "justify-center px-2",
                )}
                title={collapsed && !isMobile ? item.label : undefined}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {(!collapsed || isMobile) && <span className="whitespace-nowrap">{item.label}</span>}
                {collapsed && !isMobile && (
                  <span className="absolute left-full ml-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-200 whitespace-nowrap pointer-events-none shadow-lg border border-border z-50">
                    {item.label}
                  </span>
                )}
              </Link>
            )
          })}
        </nav>

        {/* User Info */}
        {user && (
          <div className="border-t border-sidebar-border p-4">
            <div
              className={cn(
                "flex items-center gap-3 rounded-lg bg-sidebar-accent/50 p-3",
                collapsed && !isMobile && "justify-center p-2",
              )}
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/20">
                <User className="h-4 w-4 text-primary" />
              </div>
              {(!collapsed || isMobile) && (
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-sidebar-foreground truncate">{user.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* System Status */}
        <div className="border-t border-sidebar-border p-4">
          <div className={cn("space-y-3 rounded-lg bg-sidebar-accent/50 p-3", collapsed && !isMobile && "p-2")}>
            <div
              className={cn("flex items-center text-xs", collapsed && !isMobile ? "justify-center" : "justify-between")}
            >
              <div className="flex items-center gap-2 text-sidebar-foreground">
                <Activity className="h-4 w-4 shrink-0" />
                {(!collapsed || isMobile) && <span className="whitespace-nowrap">System Status</span>}
              </div>
              {(!collapsed || isMobile) && <span className="flex h-2 w-2 rounded-full bg-green-500" />}
            </div>
            {(!collapsed || isMobile) && (
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 text-sidebar-foreground">
                  <Database className="h-4 w-4 shrink-0" />
                  <span className="whitespace-nowrap">Active Sensors</span>
                </div>
                <span className="font-semibold text-sidebar-foreground">3</span>
              </div>
            )}
          </div>
        </div>

        {/* Dark Mode & Logout */}
        <div className="border-t border-sidebar-border p-4 space-y-1">
          <button
            onClick={toggleDarkMode}
            className={cn(
              "flex w-full items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium text-sidebar-foreground transition-all duration-200 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              collapsed && !isMobile && "justify-center px-2",
            )}
            title={collapsed && !isMobile ? (isDark ? "Light Mode" : "Dark Mode") : undefined}
          >
            {isDark ? <Sun className="h-5 w-5 shrink-0" /> : <Moon className="h-5 w-5 shrink-0" />}
            {(!collapsed || isMobile) && (
              <span className="whitespace-nowrap">{isDark ? "Light Mode" : "Dark Mode"}</span>
            )}
          </button>

          <button
            onClick={handleLogout}
            disabled={isLoggingOut}
            className={cn(
              "flex w-full items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium text-destructive transition-all duration-200 hover:bg-destructive/10",
              collapsed && !isMobile && "justify-center px-2",
            )}
            title={collapsed && !isMobile ? "Log out" : undefined}
          >
            <LogOut className="h-5 w-5 shrink-0" />
            {(!collapsed || isMobile) && (
              <span className="whitespace-nowrap">{isLoggingOut ? "Logging out..." : "Log out"}</span>
            )}
          </button>
        </div>
      </div>
    </aside>
  )
}
