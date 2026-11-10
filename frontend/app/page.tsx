"use client"

import { useEffect, useRef, useState } from "react"
import { Button } from "@/registry/default/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/registry/default/ui/select"
import { useToast } from "@/registry/default/ui/use-toast"

import { DebugImages } from "@/components/debug-images"
import { NewGame } from "@/components/new-game"

const DotBgStyle = {
  backgroundImage: "radial-gradient(#888888 0.75px, transparent 0)",
  backgroundSize: "32px 32px",
  backgroundPosition: "-19px -19px",
  minHeight: "calc(100vh - 5rem)",
}

function LoadingIcon() {
  return (
    <div role="status inline-block">
      <svg
        aria-hidden="true"
        className="inline-block h-4 w-4 animate-spin fill-blue-600 text-gray-200 dark:text-gray-600"
        viewBox="0 0 100 101"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z"
          fill="currentColor"
        />
        <path
          d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z"
          fill="currentFill"
        />
      </svg>
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export default function IndexPage() {
  const { toast } = useToast()
  const [selectedCamera, setSelectedCamera] = useState<Number>(0)
  const [cameraList, setCameraList] = useState<string[]>([])
  useEffect(() => {
    fetch("/api/camera/list")
      .then((res) => res.json())
      .then((data) => {
        setCameraList(data.available_camera_ports)
        setSelectedCamera(data.selected_camera_port)
      })
  }, [])
  function switchCamera(camera: string) {
    fetch("/api/camera/switch", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ camera_id: Number.parseInt(camera) }),
    })
      .then((res) => res.json())
      .then((data) => {
        setSelectedCamera(Number.parseInt(camera))
      })
  }
  function resetCamera() {
    fetch("/api/camera/reset", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    }).then((res) => res.json())
    setTimeout(() => {
      window.location.href = "/"
    }, 500)
  }

  const visualizationImage = useRef<HTMLImageElement>(null)

  // Refresh images every 1 second
  useEffect(() => {
    const interval = setInterval(() => {
      if (visualizationImage.current) {
        visualizationImage.current.src =
          "/api/vision/visualization_frame?t=" + Date.now()
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  const getHint = async () => {
    try {
      const response = await fetch("/api/xiangqi/get_hint")
      const hint = await response.json()
      if (!response.ok) {
        throw new Error(hint.detail || "Could not get a hint.")
      }
      toast({
        title: "Hint",
        description: hint.best_move
          ? `Best move: ${hint.best_move} (depth ${hint.depth})`
          : "No legal move returned by the engine.",
        duration: 3000,
      })
    } catch (error) {
      toast({
        title: "Hint unavailable",
        description: error instanceof Error ? error.message : "Network error",
        duration: 5000,
      })
    }
  }

  const [currentGame, setCurrentGame] = useState<any>({ is_playing: false })
  const warningCooldown = useRef(0)
  const errorCooldown = useRef(0)
  const announcedWinner = useRef<string | null>(null)
  const moveHistory = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (moveHistory.current) moveHistory.current.scrollTop = 0
  }, [currentGame.moves?.length])
  useEffect(() => {
    let active = true
    let timer: ReturnType<typeof setTimeout>
    const refresh = async () => {
      try {
        const response = await fetch("/api/xiangqi/game_snapshot")
        const data = await response.json()
        if (!response.ok) throw new Error(data.detail || "Could not read the game.")
        if (!active) return
        setCurrentGame(data)
        if (data.warning && Date.now() >= warningCooldown.current) {
          window.alert(data.warning)
          warningCooldown.current = Date.now() + 5000
        }
        if (data.winner && announcedWinner.current !== data.winner) {
          announcedWinner.current = data.winner
          window.alert(data.winner === data.player
            ? "You win: COM has no legal moves (checkmate or stalemate)."
            : "COM wins: you have no legal moves (checkmate or stalemate).")
        }
      } catch (error) {
        if (active && Date.now() >= errorCooldown.current) {
          errorCooldown.current = Date.now() + 5000
          toast({
          title: "Game update failed",
          description: error instanceof Error ? error.message : "Network error",
          duration: 3000,
          })
        }
      } finally {
        if (active) timer = setTimeout(refresh, 1000)
      }
    }
    refresh()
    return () => { active = false; clearTimeout(timer) }
  }, [toast])
  const isPlaying = currentGame.is_playing
  const isYourTurn = isPlaying && currentGame.next_player === currentGame.player

  const play = async () => {
    try {
      const response = await fetch("/api/xiangqi/play", { method: "POST" })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Could not end the turn.")
      setCurrentGame(data)
    } catch (error) {
      toast({
        title: "Turn not ended",
        description: error instanceof Error ? error.message : "Network error",
        duration: 5000,
      })
    }
  }

  return (
    <div style={DotBgStyle} className="pt-6">
      <section className="container flex flex-row gap-8 py-2">
        <div className="flex w-[250px] flex-col gap-4">
          <h2 className="text-xl font-semibold leading-none">Board Camera</h2>
          <img
            src="/api/vision/original_frame"
            className="rounded-md"
            width={320}
            height={240}
            alt="Viz Image"
          />
          <Select
            onValueChange={(value) => switchCamera(value)}
            value={selectedCamera.toString()}
          >
            <SelectTrigger id="camera">
              <SelectValue placeholder="Select Camera">
                Camera:&nbsp;{selectedCamera.toLocaleString()}
              </SelectValue>
            </SelectTrigger>
            <SelectContent position="popper">
              {cameraList.map((camera) => (
                <SelectItem value={camera} key={camera}>
                  Camera:&nbsp;{camera}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            className="w-full"
            onClick={() => {
              resetCamera()
            }}
          >
            Reset Camera
          </Button>
          <div>
            Visualization of current board camera. Please make sure the board is
            in the center of the camera and all ARUCO markers are visible.
          </div>
        </div>
        <div className="flex flex-col gap-2">
          {isPlaying && (
            <div className="text-center text-xl font-bold" aria-live="polite">
              YOU {isYourTurn && !currentGame.winner ? "●" : ""} | COM {(!isYourTurn && !currentGame.winner) ? "●" : ""}
            </div>
          )}
          <img
            ref={visualizationImage}
            src="/api/vision/visualization_frame"
            className="w-full max-w-[500px] rounded-md"
            width={500}
            height={500}
            alt="Viz Image"
          />
          <NewGame><Button className="w-full">New Game</Button></NewGame>
          <Button className="w-full" onClick={play} disabled={!isYourTurn || !!currentGame.winner}>
            End Turn
          </Button>
        </div>
        <div className="flex w-[250px] flex-col gap-2">
          {isPlaying && (
            <div className="text-sm">Analyzer difficulty: {currentGame.difficulty}</div>
          )}
          <Button className="w-full" onClick={getHint} disabled={!isYourTurn || !!currentGame.winner}>
            Hint
          </Button>
          {/* <Button className="w-full" disabled={!isPlaying}>
            AI Analyzer
          </Button> */}
          {!isPlaying && (
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Click <b>New Game</b> to start a new game from current position.
            </div>
          )}
          {isPlaying && <div className="flex flex-col gap-2">
            <h2 className="mt-4 text-xl font-semibold leading-none">
              Move History
            </h2>
            <div ref={moveHistory} className="max-h-[100px] w-full overflow-y-auto">
              <table className="flex flex-col gap-1">
                <thead className="border-b-2 border-gray-600">
                  <tr className="flex flex-row gap-1 text-left">
                    <th className="w-1/2">ID</th>
                    <th className="w-1/2">Move</th>
                  </tr>
                </thead>
                <tbody>
                  {currentGame.moves?.map((move: string, index: number) => (
                    <tr className="flex flex-row gap-1" key={index}>
                      <td className="w-1/2">{index + 1}</td>
                      <td className="w-1/2">{move}</td>
                    </tr>
                  )).reverse()}
                </tbody>
              </table>
            </div>
          </div>}
        </div>
      </section>
      <section className="container mt-4 grid items-center gap-2 py-2">
        <DebugImages />
      </section>
    </div>
  )
}
