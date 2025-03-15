"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

// --- Interfaces ---
interface PlayerStats {
  name: string;
  civilization: number;
  winner: boolean;
  military_score: number;
  economy_score: number;
  technology_score: number;
  society_score: number;
  units_killed: number;
  buildings_destroyed: number;
  resources_gathered: number;
  fastest_castle_age: number;
  fastest_imperial_age: number;
  relics_collected: number;
}

interface MapData {
  name: string;
  size: string;
}

interface GameStats {
  id: number;
  game_version: string;
  map: MapData | string;
  game_type: string;
  duration: number; // stored as total seconds in your DB
  players: PlayerStats[];
  timestamp: string;
}

// --- Helper to clean up "game_type" string ---
function cleanGameType(rawType: string): string {
  // Example input: "(<Version.DE: 21>, 'VER 9.4', 63.0, 5, 133431)"
  // We extract 'VER 9.4'
  const match = rawType.match(/'(VER.*?)'/);
  return match && match[1] ? match[1] : rawType;
}

// --- Helper to format duration from total seconds to "X hours Y minutes Z seconds" style ---
function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const remainder = totalSeconds % 3600;
  const minutes = Math.floor(remainder / 60);
  const secs = remainder % 60;

  const hourStr = hours === 1 ? "1 hour" : `${hours} hours`;
  const minStr = minutes === 1 ? "1 minute" : `${minutes} minutes`;
  const secStr = secs === 1 ? "1 second" : `${secs} seconds`;

  if (hours > 0 && minutes > 0 && secs > 0) {
    return `${hourStr} ${minStr} ${secStr}`;
  } else if (hours > 0 && minutes > 0) {
    return `${hourStr} ${minStr}`;
  } else if (hours > 0) {
    return hourStr;
  } else if (minutes > 0 && secs > 0) {
    return `${minStr} ${secStr}`;
  } else if (minutes > 0) {
    return minStr;
  } else {
    return secStr;
  }
}

const GameStatsPage: React.FC = () => {
  const router = useRouter();
  const [games, setGames] = useState<GameStats[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchGameStats = async (): Promise<void> => {
      try {
        // Cache-buster to avoid stale responses.
        const response = await fetch(
          `http://localhost:8002/api/game_stats?ts=${Date.now()}`,
          { cache: "no-store" }
        );
        const data = (await response.json()) as GameStats[];
        console.log("🔍 RAW API Response:", data);

        if (!Array.isArray(data)) {
          console.warn("⚠️ No game stats array found in API response.");
          setLoading(false);
          return;
        }

        // Convert fields that might be stored as JSON strings.
        const formattedGames: GameStats[] = data.map((game: GameStats): GameStats => {
          const safePlayers: PlayerStats[] =
            typeof game.players === "string"
              ? (JSON.parse(game.players) as PlayerStats[])
              : game.players;

          let safeMap: MapData | string = game.map;
          if (typeof safeMap === "string") {
            try {
              safeMap = JSON.parse(safeMap) as MapData;
            } catch {
              // Fallback: keep as string.
            }
          }

          return {
            ...game,
            players: safePlayers,
            map: safeMap,
          };
        });

        // Filter out games with empty players.
        const validGames: GameStats[] = formattedGames.filter(
          (g: GameStats) => g.players && g.players.length > 0
        );
        if (validGames.length === 0) {
          console.warn("⚠️ All parsed games have empty player lists.");
          setLoading(false);
          return;
        }

        // Sort games by timestamp (newest first).
        // Replace the space with "T" so the string parses as ISO format.
        validGames.sort((a: GameStats, b: GameStats) => {
          const dateA = new Date(a.timestamp.replace(" ", "T")).valueOf();
          const dateB = new Date(b.timestamp.replace(" ", "T")).valueOf();
          return dateB - dateA;
        });

        setGames(validGames);
        setLoading(false);
      } catch (err) {
        console.error("❌ Error fetching game stats:", err);
        setLoading(false);
      }
    };

    fetchGameStats();
    // Optional: auto-refresh every 3 seconds.
    const interval = setInterval(fetchGameStats, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <h2 className="text-3xl font-bold text-center mb-6 text-gray-400">
        Game Stats
      </h2>

      {loading ? (
        <p className="text-center text-gray-400">Loading game stats...</p>
      ) : games.length === 0 ? (
        <p className="text-center text-gray-400">No game stats available.</p>
      ) : (
        <div className="space-y-6">
          {games.map((game: GameStats, index: number) => {
            // The newest game is index=0 ("Latest Match")
            const isLatest = index === 0;
            return (
              <div
                key={game.id}
                className={`p-6 rounded-xl shadow-lg transition-all ${
                  isLatest
                    ? "bg-gray-900 text-yellow-400 border-2 border-yellow-500"
                    : "bg-gray-700 text-black border border-gray-600"
                }`}
              >
                <h3 className="text-2xl font-semibold">
                  {isLatest
                    ? "🔥 Latest Match"
                    : `Previous Match #${games.length - index}`}
                </h3>
                <p className="text-lg mt-2">
                  <strong>Game Version:</strong> {game.game_version}
                </p>
                <p className="text-lg">
                  <strong>Map:</strong>{" "}
                  {typeof game.map === "object" ? game.map?.name : game.map}
                </p>
                <p className="text-lg">
                  <strong>Game Type:</strong> {cleanGameType(game.game_type)}
                </p>
                <p className="text-lg">
                  <strong>Duration:</strong> {formatDuration(game.duration)}
                </p>

                <h4 className="text-xl font-semibold mt-4">Players</h4>
                <div className="mt-2 space-y-2">
                  {game.players.map((player: PlayerStats, idx: number) => (
                    <div
                      key={idx}
                      className={`p-4 rounded-lg ${
                        player.winner
                          ? "bg-gray-500 text-black font-bold"
                          : "bg-gray-600 text-black"
                      }`}
                    >
                      <p>
                        <strong>Name:</strong> {player.name}{" "}
                        {player.winner && "🏆"}
                      </p>
                      <p>
                        <strong>Civilization:</strong> {player.civilization}
                      </p>
                      <p>
                        <strong>Military Score:</strong> {player.military_score}
                      </p>
                      <p>
                        <strong>Economy Score:</strong> {player.economy_score}
                      </p>
                      <p>
                        <strong>Technology Score:</strong> {player.technology_score}
                      </p>
                      <p>
                        <strong>Society Score:</strong> {player.society_score}
                      </p>
                      <p>
                        <strong>Units Killed:</strong> {player.units_killed}
                      </p>
                      <p>
                        <strong>Buildings Destroyed:</strong> {player.buildings_destroyed}
                      </p>
                      <p>
                        <strong>Resources Gathered:</strong> {player.resources_gathered}
                      </p>
                      <p>
                        <strong>Fastest Castle Age:</strong> {player.fastest_castle_age} seconds
                      </p>
                      <p>
                        <strong>Fastest Imperial Age:</strong> {player.fastest_imperial_age} seconds
                      </p>
                      <p>
                        <strong>Relics Collected:</strong> {player.relics_collected}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="text-center mt-8">
        <Button
          className="bg-blue-700 hover:bg-blue-700 px-6 py-3 text-white font-semibold"
          onClick={() => router.push("/")}
        >
          ⬅️ Back to Home
        </Button>
      </div>
    </div>
  );
};

export default GameStatsPage;
