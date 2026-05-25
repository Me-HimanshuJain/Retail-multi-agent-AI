"""Standalone simulation runner."""

from __future__ import annotations

import argparse
import asyncio

from src.simulation.environment import RetailSimulator


async def main(days: int, seed: int) -> None:
    sim = RetailSimulator(seed=seed)
    await sim.run(days=days)
    print(sim.get_metrics())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run retail simulation")
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    asyncio.run(main(args.days, args.seed))
