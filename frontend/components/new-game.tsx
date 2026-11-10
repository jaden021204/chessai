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

  const newGame = async () => {
    try {
      const response = await fetch("/api/xiangqi/new_game", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ next_player: nextPlayer, difficulty }),
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
            Analyzer mode: start a game from the current board.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-2">
          <label htmlFor="next_player">Next Player</label>
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
