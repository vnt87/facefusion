interface MainLayoutProps {
    children: React.ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
    return (
        <div className="min-h-screen bg-zinc-900">
            <div className="h-full min-h-screen bg-zinc-900 px-6 py-8 lg:px-10">
                {children}
            </div>
        </div>
    )
}
