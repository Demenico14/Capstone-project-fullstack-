"use client"

import { Menu, Sprout, User } from "lucide-react"
import { Button } from "@/components/ui/button"

interface MobileHeaderProps {
  user?: { name: string; email: string } | null
  isOpen: boolean
  onToggle: () => void
}

export function MobileHeader({ user, isOpen, onToggle }: MobileHeaderProps) {
  return (
    <header className="lg:hidden fixed top-0 left-0 right-0 z-30 h-16 bg-sidebar border-b border-sidebar-border px-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className="text-sidebar-foreground"
          aria-label={isOpen ? "Close menu" : "Open menu"}
        >
          <Menu className="h-6 w-6" />
        </Button>
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Sprout className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="font-bold text-sidebar-foreground">CropIoT</span>
        </div>
      </div>

      {user && (
        <div className="flex items-center gap-2 text-sidebar-foreground">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20">
            <User className="h-4 w-4 text-primary" />
          </div>
          <span className="text-sm font-medium hidden sm:inline">{user.name}</span>
        </div>
      )}
    </header>
  )
}
