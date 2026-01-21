import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import { LayoutDashboard, Settings, Sparkles, Wand2 } from "lucide-react"

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> { }

export function Sidebar({ className }: SidebarProps) {
    return (
        <div className={cn("pb-12 min-h-screen bg-zinc-950", className)}>
            <div className="space-y-4 py-4">
                <div className="px-3 py-2">
                    <div className="flex items-center gap-2 px-4 mb-6">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-red-500 to-orange-500">
                            <Sparkles className="h-4 w-4 text-white" />
                        </div>
                        <h2 className="text-lg font-semibold tracking-tight text-white">
                            FaceFusion
                        </h2>
                    </div>
                    <div className="space-y-1">
                        <Button variant="secondary" className="w-full justify-start gap-2 bg-zinc-800 text-white hover:bg-zinc-700">
                            <LayoutDashboard className="h-4 w-4" />
                            Dashboard
                        </Button>
                    </div>
                </div>
                <Separator className="bg-zinc-800" />
                <div className="px-3 py-2">
                    <h2 className="mb-2 px-4 text-xs font-semibold uppercase tracking-wider text-zinc-500">
                        Processors
                    </h2>
                    <ScrollArea className="h-[200px]">
                        <div className="space-y-1">
                            <Button variant="ghost" className="w-full justify-start gap-2 text-zinc-400 hover:text-white hover:bg-zinc-800">
                                <Wand2 className="h-4 w-4" />
                                Face Swapper
                            </Button>
                            <Button variant="ghost" className="w-full justify-start gap-2 text-zinc-400 hover:text-white hover:bg-zinc-800">
                                <Sparkles className="h-4 w-4" />
                                Face Enhancer
                            </Button>
                        </div>
                    </ScrollArea>
                </div>
                <Separator className="bg-zinc-800" />
                <div className="px-3 py-2">
                    <div className="space-y-1">
                        <Button variant="ghost" className="w-full justify-start gap-2 text-zinc-400 hover:text-white hover:bg-zinc-800">
                            <Settings className="h-4 w-4" />
                            Settings
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    )
}
