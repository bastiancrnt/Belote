import random

numbers   = [80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150, 155, 160]
suits     = ["K", "P", "C", "T", "SA", "TA"]


class Bidding:
    def __init__(self, suit, points):
        self.suit      = suit
        self.points    = points
        self.coinche    = False
        self.surcoinche = False

    def __str__(self):
        return f"suit:{self.suit}, points:{self.points}"


def run_bidding(first_player=0, hands=None, agents=None, verbose=False):
    """
    Simule les enchères.
    Si `hands` et `agents` sont fournis, chaque agent décide pour son joueur.
    Sinon, les annonces sont aléatoires.
    Retourne (Bidding, contract_team) ou (None, None).
    """
    current_best = 0
    passe        = 0
    contracts    = []   # (player_idx, Bidding | "pass")

    player_bids = {}   # player_idx -> Bidding (dernière enchère valide)

    def make_bid(player_idx):
        if agents is not None and hands is not None:
            partner_idx = (player_idx + 2) % 4
            partner_bid = player_bids.get(partner_idx)
            partner_info = (partner_bid.suit, partner_bid.points) if partner_bid else None
            result = agents[player_idx].choose_bid(hands[player_idx], current_best, partner_info)
            if result is None:
                return "pass"
            suit, pts = result
            if pts not in numbers or pts <= current_best:
                return "pass"
            return Bidding(suit, pts)
        else:
            available = [n for n in numbers if n > current_best]
            if not available or random.choice(["pass", "bid"]) == "pass":
                return "pass"
            return Bidding(random.choice(suits), random.choice(available))

    SUIT_SYMBOLS = {"C": "♦", "K": "♥", "P": "♠", "T": "♣", "SA": "SA", "TA": "TA"}

    def log_bid(player_idx, bid):
        if not verbose:
            return
        if bid == "pass":
            print(f"  J{player_idx}: passe")
        else:
            sym = SUIT_SYMBOLS.get(bid.suit, bid.suit)
            print(f"  J{player_idx}: {bid.points} à {sym}")

    if verbose:
        print("  -- Enchères --")

    # Premier joueur
    bid = make_bid(first_player)
    contracts.append((first_player, bid))
    log_bid(first_player, bid)
    if bid != "pass":
        player_bids[first_player] = bid
        current_best = bid.points

    while passe < 3:
        player_idx = (first_player + len(contracts)) % 4
        bid = make_bid(player_idx)
        log_bid(player_idx, bid)
        if bid == "pass":
            contracts.append((player_idx, "pass"))
            passe += 1
        else:
            contracts.append((player_idx, bid))
            player_bids[player_idx] = bid
            current_best = bid.points
            passe = 0

    for player_idx, bid in reversed(contracts):
        if bid != "pass":
            return bid, player_idx % 2

    return None, None
