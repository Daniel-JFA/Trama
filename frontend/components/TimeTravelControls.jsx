"use client";

import { useState, useEffect, useRef, useCallback } from "react";

export default function TimeTravelControls({
  graph,
  maxWeeks = 12,
  currentWeek,
  onWeekChange,
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(800); // ms per step
  const timerRef = useRef(null);

  // Compute aggregate weekly distribution for scrubber background sparkline
  const weeklyTotals = Array(maxWeeks).fill(0);
  if (graph?.nodes) {
    graph.nodes.forEach((n) => {
      if (n.act && Array.isArray(n.act)) {
        n.act.slice(0, maxWeeks).forEach((c, i) => {
          weeklyTotals[i] += c;
        });
      }
    });
  }
  const maxWeeklyVol = Math.max(...weeklyTotals, 1);

  const handleNext = useCallback(() => {
    onWeekChange((prev) => {
      if (prev === null) return 1;
      if (prev >= maxWeeks) return 1;
      return prev + 1;
    });
  }, [maxWeeks, onWeekChange]);

  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        handleNext();
      }, playbackSpeed);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, playbackSpeed, handleNext]);

  return (
    <div className="timetravel-bar">
      <div className="timetravel-left">
        <button
          className={`timetravel-btn-play ${isPlaying ? "timetravel-btn-playing" : ""}`}
          onClick={() => setIsPlaying(!isPlaying)}
          title={isPlaying ? "Pausar evolución temporal" : "Reproducir evolución temporal"}
        >
          {isPlaying ? "⏸" : "▶"}
        </button>
        <button
          className={`timetravel-btn-all ${currentWeek === null ? "timetravel-btn-active" : ""}`}
          onClick={() => {
            setIsPlaying(false);
            onWeekChange(null);
          }}
        >
          Global (12 sem.)
        </button>
      </div>

      <div className="timetravel-slider-wrap">
        {/* Background micro activity histogram in slider track */}
        <div className="timetravel-micro-histogram">
          {weeklyTotals.map((tot, i) => {
            const h = Math.max(15, (tot / maxWeeklyVol) * 100);
            const isSpike = i === 5 || i === 6; // S6, S7
            return (
              <div
                key={i}
                className="timetravel-micro-bar"
                style={{
                  height: `${h}%`,
                  background: isSpike
                    ? "rgba(224, 96, 184, 0.45)"
                    : "rgba(139, 124, 246, 0.22)",
                }}
              />
            );
          })}
        </div>

        <input
          type="range"
          min="1"
          max={maxWeeks}
          value={currentWeek === null ? maxWeeks : currentWeek}
          onChange={(e) => {
            setIsPlaying(false);
            onWeekChange(parseInt(e.target.value, 10));
          }}
          className="timetravel-range"
        />

        <div className="timetravel-ticks">
          {Array.from({ length: maxWeeks }, (_, i) => i + 1).map((w) => {
            const isSpike = w === 6 || w === 7;
            const isCurrent = currentWeek === w;
            return (
              <span
                key={w}
                className={`timetravel-tick ${isCurrent ? "timetravel-tick-active" : ""} ${
                  isSpike ? "timetravel-tick-alert" : ""
                }`}
                onClick={() => {
                  setIsPlaying(false);
                  onWeekChange(w);
                }}
              >
                S{w}
                {isSpike && <span className="tick-spike-dot" />}
              </span>
            );
          })}
        </div>
      </div>

      <div className="timetravel-right">
        <span className="timetravel-badge">
          {currentWeek === null ? "Vista Acumulada" : `Semana ${currentWeek}`}
        </span>
        {(currentWeek === 6 || currentWeek === 7) && (
          <span className="timetravel-alert-badge">⚡ Pico Astroturfing</span>
        )}
      </div>
    </div>
  );
}
