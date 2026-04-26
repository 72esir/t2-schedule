import { createContext, useCallback, useContext, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { CheckCircle2, XCircle, X } from 'lucide-react'

export type ToastType = 'success' | 'error'

interface ToastItem {
    id: number
    type: ToastType
    message: string
}

interface ToastContextValue {
    toast: (message: string, type?: ToastType) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
    const [toasts, setToasts] = useState<ToastItem[]>([])
    const counter = useRef(0)

    const toast = useCallback((message: string, type: ToastType = 'success') => {
        const id = ++counter.current
        setToasts((prev) => [...prev, { id, type, message }])
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id))
        }, 4000)
    }, [])

    function dismiss(id: number) {
        setToasts((prev) => prev.filter((t) => t.id !== id))
    }

    return (
        <ToastContext.Provider value={{ toast }}>
            {children}
            <div
                aria-live="polite"
                className="pointer-events-none fixed bottom-6 right-4 z-50 flex flex-col items-end gap-3 sm:right-6"
            >
                {toasts.map((item) => (
                    <div
                        key={item.id}
                        className={`pointer-events-auto flex max-w-sm items-center gap-3 rounded-xl border px-4 py-3 shadow-xl backdrop-blur-sm animate-in slide-in-from-right-full fade-in duration-300 ${item.type === 'error'
                                ? 'border-[#ff3495]/30 bg-[#ff3495]/10 text-black'
                                : 'border-[#a7fc00]/50 bg-[#a7fc00]/90 text-black'
                            }`}
                    >
                        {item.type === 'error' ? (
                            <XCircle size={18} className="shrink-0 text-[#ff3495]" aria-hidden="true" />
                        ) : (
                            <CheckCircle2 size={18} className="shrink-0 text-black" aria-hidden="true" />
                        )}
                        <p className="text-sm font-bold">{item.message}</p>
                        <button
                            type="button"
                            onClick={() => dismiss(item.id)}
                            className="ml-1 shrink-0 rounded-md p-0.5 opacity-60 hover:opacity-100 transition"
                            aria-label="Закрыть"
                        >
                            <X size={14} />
                        </button>
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    )
}

export function useToast() {
    const ctx = useContext(ToastContext)
    if (!ctx) throw new Error('useToast must be used inside ToastProvider')
    return ctx.toast
}
