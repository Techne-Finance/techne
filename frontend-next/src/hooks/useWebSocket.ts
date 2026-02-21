/**
 * useWebSocket — Real-time portfolio updates
 * 
 * Strategy: Polling-based since backend doesn't expose a WebSocket endpoint.
 * Polls portfolio, positions, and agent status at configurable intervals.
 * Emits events that React Query caches pick up automatically via refetch.
 * 
 * When a backend WS endpoint is added, this hook can be upgraded to use
 * native WebSocket with the same consumer API.
 */
import { useEffect, useRef, useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

export interface WebSocketConfig {
    /** Wallet address to poll for */
    walletAddress?: string
    /** Agent address for agent-specific updates */
    agentAddress?: string
    /** Polling interval in ms (default: 30s) */
    interval?: number
    /** Whether polling is enabled */
    enabled?: boolean
}

export interface WebSocketState {
    /** Whether the poller is active */
    isConnected: boolean
    /** Last update timestamp */
    lastUpdate: Date | null
    /** Number of successful polls */
    pollCount: number
    /** Last error if any */
    error: string | null
}

export function useWebSocket(config: WebSocketConfig) {
    const { walletAddress, agentAddress, interval = 30_000, enabled = true } = config
    const queryClient = useQueryClient()
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
    const [state, setState] = useState<WebSocketState>({
        isConnected: false,
        lastUpdate: null,
        pollCount: 0,
        error: null,
    })

    const invalidateQueries = useCallback(() => {
        if (!walletAddress) return

        // Invalidate all portfolio-related queries to trigger refetch
        const queries = [
            ['portfolio', walletAddress],
            ['positions', walletAddress],
            ['agent-status', walletAddress],
            ['trade-history'],
            ['audit-recent'],
        ]

        if (agentAddress) {
            queries.push(
                ['trust-score', agentAddress],
                ['session-key', agentAddress],
            )
        }

        queries.forEach(key => {
            queryClient.invalidateQueries({ queryKey: key })
        })

        setState(prev => ({
            ...prev,
            lastUpdate: new Date(),
            pollCount: prev.pollCount + 1,
            error: null,
        }))
    }, [walletAddress, agentAddress, queryClient])

    // Start/stop polling
    useEffect(() => {
        if (!enabled || !walletAddress) {
            if (intervalRef.current) {
                clearInterval(intervalRef.current)
                intervalRef.current = null
            }
            setState(prev => ({ ...prev, isConnected: false }))
            return
        }

        setState(prev => ({ ...prev, isConnected: true }))

        // Initial poll after 2s
        const initTimeout = setTimeout(() => invalidateQueries(), 2000)

        // Regular polling
        intervalRef.current = setInterval(invalidateQueries, interval)

        return () => {
            clearTimeout(initTimeout)
            if (intervalRef.current) {
                clearInterval(intervalRef.current)
                intervalRef.current = null
            }
            setState(prev => ({ ...prev, isConnected: false }))
        }
    }, [enabled, walletAddress, interval, invalidateQueries])

    // Manual refresh
    const refresh = useCallback(() => {
        invalidateQueries()
    }, [invalidateQueries])

    return { ...state, refresh }
}
