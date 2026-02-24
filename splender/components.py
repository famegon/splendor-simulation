class Card:
    """스플렌더의 발전 카드를 나타내는 클래스"""
    def __init__(self, card_id, tier, bonus, points, cost):
        self.id = card_id          # 예: "C001"
        self.tier = tier           # 1, 2, 3
        self.bonus = bonus         # "white", "blue", "green", "red", "black"
        self.points = points       # 0 ~ 5
        self.cost = cost           # 색상별 필요 토큰 딕셔너리

    def __repr__(self):
        # 개발 중 print()를 찍었을 때 카드를 알아보기 쉽게 표현해주는 마법 함수
        return f"<Card {self.id} (T{self.tier}): {self.points}pt, bonus {self.bonus}>"

    def to_dict(self):
        """현재 카드 객체를 JSON(딕셔너리) 형태로 내보냅니다."""
        return {
            "id": self.id,
            "tier": self.tier,
            "bonus": self.bonus,
            "points": self.points,
            "cost": self.cost.copy() # 원본 훼손 방지를 위해 복사본 전달
        }

    @classmethod
    def from_dict(cls, data):
        """JSON(딕셔너리) 데이터를 읽어와 Card 객체를 생성합니다."""
        return cls(
            card_id=data["id"],
            tier=data["tier"],
            bonus=data["bonus"],
            points=data["points"],
            cost=data["cost"]
        )


class Noble:
    """스플렌더의 귀족 타일을 나타내는 클래스"""
    def __init__(self, noble_id, points, requirements):
        self.id = noble_id               # 예: "N01"
        self.points = points             # 항상 3
        self.requirements = requirements # 색상별 필요 보너스 수량 딕셔너리

    def __repr__(self):
        return f"<Noble {self.id}: {self.points}pt>"

    def to_dict(self):
        """현재 귀족 객체를 JSON(딕셔너리) 형태로 내보냅니다."""
        return {
            "id": self.id,
            "points": self.points,
            "requirements": self.requirements.copy()
        }

    @classmethod
    def from_dict(cls, data):
        """JSON(딕셔너리) 데이터를 읽어와 Noble 객체를 생성합니다."""
        return cls(
            noble_id=data["id"],
            points=data["points"],
            requirements=data["requirements"]
        )
