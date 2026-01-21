import { Sidebar } from "./Sidebar"

interface MainLayoutProps {
    children: React.ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
    return (
        <div className="min-h-screen bg-zinc-900">
            <div className="grid lg:grid-cols-6">
                <Sidebar className="hidden lg:block lg:col-span-1" />
                <div className="col-span-5 lg:col-span-5">
                    <div className="h-full min-h-screen bg-zinc-900 px-6 py-8 lg:px-10">
                        {children}
                    </div>
                </div>
            </div>
        </div>
    )
}
