import random

class GreedyAgent:
    def __init__(self, player_idx):
        self.player_idx = player_idx

    def get_action(self, state):
        legal_actions = state.get_legal_actions()
        
        # 1. 구매 액션들만 필터링
        purchase_actions = [a for a in legal_actions if a['type'] == 'purchase']
        
        if purchase_actions:
            # 가장 점수가 높은 카드를 찾기 위해, 액션에 해당하는 카드 객체를 확인
            best_action = None
            max_points = -1
            
            for action in purchase_actions:
                tier = action['tier']
                card_id = action['card_id']
                source = action['source']
                
                # 보드나 예약 목록에서 해당 카드의 점수를 확인
                if source == 'board':
                    card = next(c for c in state.board[tier] if c.id == card_id)
                else:
                    player = state.players[self.player_idx]
                    card = next(c for c in player.reserved if c.id == card_id)
                
                if card.points > max_points:
                    max_points = card.points
                    best_action = action
                    
            return best_action

        # 2. 살 수 있는 카드가 없다면 토큰 가져오기 액션 필터링
        take_diff_actions = [a for a in legal_actions if a['type'] == 'take_diff']
        if take_diff_actions:
            # 가급적 3개를 꽉 채워서 가져오는 액션을 선호
            best_take = max(take_diff_actions, key=lambda x: len(x['colors']))
            return best_take

        take_same_actions = [a for a in legal_actions if a['type'] == 'take_same']
        if take_same_actions:
            return random.choice(take_same_actions)

        # 3. 토큰도 못 가져오면 예약 (공개 카드 우선)
        reserve_actions = [a for a in legal_actions if a['type'] == 'reserve_public']
        if reserve_actions:
            return random.choice(reserve_actions)

        # 4. 아무것도 안 되면 무작위 선택 (블라인드 예약 또는 패스)
        return random.choice(legal_actions)
