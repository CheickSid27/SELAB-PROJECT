"""Prix rendu livré : chaque composante est explicite et doit être datée côté données."""
from dataclasses import dataclass


@dataclass
class ComposantesPrix:
    prix_produit_fcfa: int      # par unité
    transport_total_fcfa: int
    perte_estimee_pct: float    # part du lot jugée perdue ou déclassée
    frais_fcfa: int = 0

    def prix_rendu_livre(self, quantite: int) -> float:
        """Coût par unité livrée utilisable, pertes incluses."""
        if quantite <= 0:
            raise ValueError("quantite doit être positive")
        if not 0 <= self.perte_estimee_pct < 100:
            raise ValueError("perte_estimee_pct doit être dans [0, 100[")
        utilisables = quantite * (1 - self.perte_estimee_pct / 100)
        cout_total = self.prix_produit_fcfa * quantite + self.transport_total_fcfa + self.frais_fcfa
        return round(cout_total / utilisables, 1)
