"use client"

import { useState } from "react"
import { Button } from "@/registry/default/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/registry/default/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/registry/default/ui/select"
import { useToast } from "@/registry/default/ui/use-toast"

export function NewGame({ children }: { children: React.ReactNode }) {
  const { toast } = useToast()
  const [nextPlayer, setNextPlayer] = useState<string>("r")
  const [difficulty, setDifficulty] = useState<string>("medium")
  const [position, setPosition] = useState<string>("current")
  const [timeControl, setTimeControl] = useState<string>("5")

  const newGame = async () => {
    try {
      const response = await fetch("/api/xiangqi/new_game", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ next_player: nextPlayer, difficulty, position, time_control: timeControl, mode: "analyzer" }),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "Could not start the game.")
      }
      window.location.reload()
    } catch (error) {
      toast({
        title: "Could not start game",
        description: error instanceof Error ? error.message : "Network error",
        duration: 5000,
      })
    }
  }

  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="sm:max-w-[475px]">
        <DialogHeader>
          <DialogTitle>New Game</DialogTitle>
          <DialogDescription>
            Choose a side and starting position. Your opponent&apos;s pieces
            must be at the top of the detected board. Red always moves first.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-2">
          <label htmlFor="next_player">Your side</label>
          <Select
            onValueChange={(value) => setNextPlayer(value)}
            value={nextPlayer}
          >
            <SelectTrigger id="next_player">
              <SelectValue placeholder="Next Player">
                {"r" === nextPlayer ? "Red" : "Black"}
              </SelectValue>
            </SelectTrigger>
            <SelectContent position="popper">
              <SelectItem value={"r"} key={"r"}>
                Red
              </SelectItem>
              <SelectItem value={"b"} key={"b"}>
                Black
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5 leading-none">
          <label htmlFor="mode">Mode</label>
          <Select value="analyzer">
            <SelectTrigger id="mode"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="analyzer">Analyzer</SelectItem>
              <SelectItem value="robot" disabled>vs ROBOT (not available yet)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5 leading-none">
          <label htmlFor="position">Starting position</label>
          <Select value={position} onValueChange={setPosition}>
            <SelectTrigger id="position"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="current">Current board</SelectItem>
              <SelectItem value="starting">Starting board</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5 leading-none">
          <label htmlFor="difficulty">Difficulty (search depth)</label>
          <Select value={difficulty} onValueChange={setDifficulty}>
            <SelectTrigger id="difficulty">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="easy">Easy (2)</SelectItem>
              <SelectItem value="medium">Medium (4)</SelectItem>
              <SelectItem value="hard">Hard (6)</SelectItem>
              <SelectItem value="expert">Expert (8)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5 leading-none">
          <label htmlFor="time_control">Timer</label>
          <Select value={timeControl} onValueChange={setTimeControl}>
            <SelectTrigger id="time_control"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="5">5 minutes</SelectItem>
              <SelectItem value="5+5">5 minutes + 5 seconds</SelectItem>
              <SelectItem value="10">10 minutes</SelectItem>
              <SelectItem value="10+5">10 minutes + 5 seconds</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <DialogFooter>
          <Button
            className="w-full"
            onClick={() => {
              newGame()
            }}
          >
            Continue
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
