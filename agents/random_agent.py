import random

class RandomAgent:
    def __init__(self, player_idx):
        self.player_idx = player_idx

    def get_action(self, state):
        """
        현재 상태에서 가능한 합법적 행동(Legal Actions) 중 
        무작위로 하나를 골라 반환합니다.
        """
        # 현재 엔진에서 유효한 액션 목록 뽑아오기
        legal_actions = state.get_legal_actions()
        
        # 무작위로 하나 선택
        return random.choice(legal_actions)
