"""
Scoring — Technique 1
=====================
Contrat réussi (preneur >= contrat) :
    preneur  : points_cartes + contrat
    défense  : points_cartes

Contrat chuté (preneur < contrat) :
    preneur  : 0
    défense  : contrat + 160

Source de vérité unique utilisée par benchmark.py et game.py.
"""


def apply_contract(pts0: int, pts1: int, contract: int, contract_team: int):
    """Calcule les scores de la donne selon la Technique 1.

    Args:
        pts0          : points de cartes remportés par l'équipe 0
        pts1          : points de cartes remportés par l'équipe 1
        contract      : valeur du contrat annoncé
        contract_team : équipe preneuse (0 ou 1)

    Returns:
        (score_eq0, score_eq1) après application du contrat
    """
    takers = pts0 if contract_team == 0 else pts1
    if takers >= contract:
        # Succès : preneur garde ses points + contrat, défenseur garde ses points
        if contract_team == 0:
            return pts0 + contract, pts1
        else:
            return pts0, pts1 + contract
    else:
        # Chute : preneur = 0, défenseur = contrat + 160
        if contract_team == 0:
            return 0, contract + 160
        else:
            return contract + 160, 0
