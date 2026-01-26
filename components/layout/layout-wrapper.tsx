"use client"

import type React from "react"
import { Sidebar } from "./sidebar"
import { MobileHeader } from "./mobile-header"
import { useState, useEffect } from "react"
import { usePathname, useRouter } from "next/navigation"

export function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)
  const [user, setUser] = useState<{ name: string; email: string } | null>(null)
  const pathname = usePathname()
  const router = useRouter()

  // Auth pages don't need sidebar
  const isAuthPage = pathname === "/login" || pathname === "/signup"

  useEffect(() => {
    setIsMobileMenuOpen(false)
  }, [pathname])

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await fetch("/api/auth/me")
        if (response.ok) {
          const data = await response.json()
          setIsAuthenticated(true)
          setUser(data.user)
        } else {
          setIsAuthenticated(false)
          setUser(null)
          if (!isAuthPage) {
            router.push("/login")
          }
        }
      } catch {
        setIsAuthenticated(false)
        setUser(null)
        if (!isAuthPage) {
          router.push("/login")
        }
      }
    }

    checkAuth()
  }, [pathname, router, isAuthPage])

  // Show nothing while checking auth to avoid flash
  if (isAuthenticated === null && !isAuthPage) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    )
  }

  // Auth pages render without sidebar
  if (isAuthPage) {
    return <>{children}</>
  }

  // Protected pages with sidebar
  if (!isAuthenticated) {
    return null
  }

  return (
    <>
      <MobileHeader user={user} isOpen={isMobileMenuOpen} onToggle={() => setIsMobileMenuOpen(!isMobileMenuOpen)} />

      <div className="hidden lg:block">
        <Sidebar isCollapsed={isCollapsed} setIsCollapsed={setIsCollapsed} user={user} />
      </div>

      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-40">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setIsMobileMenuOpen(false)} />
          <div className="absolute left-0 top-0 h-full w-72 bg-sidebar border-r border-sidebar-border animate-in slide-in-from-left duration-300">
            <Sidebar
              isCollapsed={false}
              setIsCollapsed={() => {}}
              user={user}
              onClose={() => setIsMobileMenuOpen(false)}
              isMobile
            />
          </div>
        </div>
      )}

      <main
        className={`min-h-screen bg-background transition-all duration-300 
          pt-16 lg:pt-0
          px-4 py-4 lg:p-6
          lg:${isCollapsed ? "ml-20" : "ml-64"}`}
        style={{
          marginLeft:
            typeof window !== "undefined" && window.innerWidth >= 1024 ? (isCollapsed ? "5rem" : "16rem") : "0",
        }}
      >
        {children}
      </main>
    </>
  )
}
