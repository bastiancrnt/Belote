from belote.game.game import play_game
from belote.agents.heuristic_bot import HeuristicBot

if __name__ == "__main__":
    agents = [HeuristicBot() for _ in range(4)]
    play_game(agents=agents)
