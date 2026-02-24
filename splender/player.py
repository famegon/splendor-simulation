from .components import Card, Noble

class Player:
    def __init__(self, player_id, name=None):
        self.id = player_id
        self.name = name if name else f"Player_{player_id}"
        
        # 보유 자원
        self.gems = {'white': 0, 'blue': 0, 'green': 0, 'red': 0, 'black': 0, 'gold': 0}
        self.cards = []      # 구매한 카드 리스트
        self.reserved = []   # 예약한 카드 리스트
        self.nobles = []     # 획득한 귀족 타일 리스트
        self.score = 0       # 현재 점수

    def __repr__(self):
        return f"<Player {self.id}: {self.score}pts, {sum(self.gems.values())} gems>"

    @property
    def bonuses(self):
        """구매한 카드들로부터 얻는 색상별 할인(보너스) 총합을 계산합니다."""
        bonus_counts = {'white': 0, 'blue': 0, 'green': 0, 'red': 0, 'black': 0}
        for card in self.cards:
            bonus_counts[card.bonus] += 1
        return bonus_counts

    def can_buy(self, card):
        """
        이 카드를 구매할 수 있는지(True/False) 판단합니다.
        로직: 카드 비용 - 보유 보너스 = 부족한 비용. 
        부족한 비용을 보유 보석으로 메우고, 그래도 부족하면 황금 토큰으로 충당 가능한지 확인.
        """
        missing_gems = 0
        current_bonuses = self.bonuses

        for color, cost in card.cost.items():
            if cost == 0:
                continue
            cost_after_bonus = max(0, cost - current_bonuses.get(color, 0))
            if self.gems[color] < cost_after_bonus:
                missing_gems += (cost_after_bonus - self.gems[color])
        
        return missing_gems <= self.gems['gold']

    def pay_for_card(self, card):
        """
        카드 구매를 위해 토큰을 지불하고, 지불된 토큰 딕셔너리를 반환합니다.
        
        ※ 이 함수의 책임은 '토큰 차감'에 한정됩니다.
          카드 인벤토리 추가, 점수 갱신, 예약 목록 정리는 GameState.step()이 담당합니다.
        ※ 반드시 can_buy() == True 인 상태에서만 호출해야 합니다.
        """
        paid_tokens = {'white': 0, 'blue': 0, 'green': 0, 'red': 0, 'black': 0, 'gold': 0}
        current_bonuses = self.bonuses

        for color, cost in card.cost.items():
            if cost == 0:
                continue

            # 1. 보너스 차감
            cost_after_bonus = max(0, cost - current_bonuses.get(color, 0))
            
            # 2. 일반 보석 사용 (가진 것 내에서 최대한 지불)
            gems_to_pay = min(self.gems[color], cost_after_bonus)
            self.gems[color] -= gems_to_pay
            paid_tokens[color] += gems_to_pay
            
            # 3. 황금 토큰 사용 (부족분 충당)
            gold_needed = cost_after_bonus - gems_to_pay
            if gold_needed > 0:
                self.gems['gold'] -= gold_needed
                paid_tokens['gold'] += gold_needed

        return paid_tokens

    def to_dict(self):
        """플레이어 상태를 딕셔너리로 내보냅니다 (시뮬레이션 저장용)."""
        return {
            "id": self.id,
            "name": self.name,
            "gems": self.gems.copy(),
            "cards": [c.to_dict() for c in self.cards],
            "reserved": [c.to_dict() for c in self.reserved],
            "nobles": [n.to_dict() for n in self.nobles],
            "score": self.score
        }

    @classmethod
    def from_dict(cls, data):
        """딕셔너리로부터 플레이어 상태를 복원합니다 (시뮬레이션 로딩용)."""
        player = cls(data["id"], data["name"])
        player.gems = data["gems"]
        player.cards = [Card.from_dict(c) for c in data["cards"]]
        player.reserved = [Card.from_dict(c) for c in data["reserved"]]
        player.nobles = [Noble.from_dict(n) for n in data["nobles"]]
        player.score = data["score"]
        return player
