from belote.game.bidding import run_bidding
from belote.game.hand   import Hand
from belote.core.deck   import Deck

SUIT_SYMBOLS = {"C": "♦", "K": "♥", "P": "♠", "T": "♣", "SA": "SA", "TA": "TA"}


from belote.rules.scoring import apply_contract


def play_game(agents=None, target=501, verbose=True):
    scores       = [0, 0]
    n_hand       = 0
    first_player = 0

    while max(scores) < target:
        n_hand += 1
        d = Deck()
        d.shuffle()
        hands = d.deal()   # deal d'abord pour que les agents voient leurs cartes

        bidding, contract_team = run_bidding(first_player, hands=hands, agents=agents, verbose=verbose)

        if bidding is None:
            if verbose:
                print(f"\nManche {n_hand}: tout le monde passe, redistribution")
            first_player = (first_player + 1) % 4
            continue

        sym = SUIT_SYMBOLS.get(bidding.suit, bidding.suit)
        if verbose:
            print(f"\n{'='*52}")
            print(f"  MANCHE {n_hand}  |  J{first_player} ouvre  |  Contrat : {bidding.points} à {sym}  (eq{contract_team})")
            print(f"{'='*52}")

        h = Hand(hands, bidding.suit, bidding.points, agents,
                 verbose=verbose, first_player=first_player)
        pts0, pts1 = h.play_hand()
        s0, s1     = apply_contract(pts0, pts1, bidding.points, contract_team)
        scores[0] += s0
        scores[1] += s1

        if verbose:
            reussi = (contract_team == 0 and s0 > 0) or (contract_team == 1 and s1 > 0)
            print(f"\n  Contrat {'✓ réussi' if reussi else '✗ chuté'}")
            print(f"  Score  eq0 : {scores[0]}  |  eq1 : {scores[1]}")

        first_player = (first_player + 1) % 4

    winner = 0 if scores[0] >= target else 1
    print(f"\n{'='*52}")
    print(f"  Équipe {winner} gagne ! ({scores[0]}-{scores[1]} en {n_hand} manches)")
    print(f"{'='*52}")
    return scores, winner
