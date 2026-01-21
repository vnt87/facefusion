import { useEffect, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

interface TerminalProps {
    logs: string[]
    className?: string
}

export function Terminal({ logs, className }: TerminalProps) {
    const bottomRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [logs])

    return (
        <Card className={cn('flex flex-col h-full overflow-hidden', className)}>
            <CardHeader className="pb-3 shrink-0">
                <CardTitle className="text-lg">Terminal</CardTitle>
                <CardDescription>Processing output and logs</CardDescription>
            </CardHeader>
            <CardContent className="p-0 flex-1 min-h-0">
                <ScrollArea className="h-full w-full">
                    <div className="bg-zinc-950 p-4 font-mono text-xs text-zinc-100 min-h-full">
                        {logs.length === 0 ? (
                            <div className="text-zinc-500">Waiting for processing...</div>
                        ) : (
                            logs.map((log, index) => (
                                <div key={index} className="whitespace-pre-wrap">
                                    <span className="text-zinc-500">[{String(index + 1).padStart(3, '0')}]</span>{' '}
                                    {log}
                                </div>
                            ))
                        )}
                        <div ref={bottomRef} />
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    )
}
