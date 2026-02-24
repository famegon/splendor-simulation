import random
from .player import Player
from .components import Card, Noble

class GameState:
    def __init__(self, num_players=2):
        assert 2 <= num_players <= 4, "플레이어 수는 2~4명이어야 합니다."
        self.num_players = num_players
        
        # 1. 보석 세팅 (인원수에 따라 다름)
        gem_counts = {2: 4, 3: 5, 4: 7}[num_players]
        self.bank = {
            'white': gem_counts, 'blue': gem_counts, 'green': gem_counts, 
            'red': gem_counts, 'black': gem_counts, 'gold': 5
        }
        
        # 2. 플레이어 세팅
        self.players = [Player(i) for i in range(num_players)]
        self.current_player_idx = 0
        
        # 3. 보드 상태 (덱, 깔린 카드, 귀족)
        self.decks = {1: [], 2: [], 3: []}
        self.board = {1: [], 2: [], 3: []}
        self.nobles = []

    def reset(self, all_cards, all_nobles):
        """게임을 초기 상태로 세팅합니다. (외부에서 전체 카드/귀족 리스트를 주입)"""
        # 카드 분류 및 셔플
        for card in all_cards:
            self.decks[card.tier].append(card)
            
        for tier in self.decks:
            random.shuffle(self.decks[tier])
            # 각 티어별로 4장씩 보드에 깔기
            for _ in range(4):
                if self.decks[tier]:
                    self.board[tier].append(self.decks[tier].pop())
                    
        # 귀족 셔플 및 세팅 (인원수 + 1)
        random.shuffle(all_nobles)
        self.nobles = all_nobles[:self.num_players + 1]

    # ==========================================
    # 턴 진행 파이프라인 (명곤 님의 3단계 룰 완벽 반영)
    # ==========================================
    def step(self, action):
        """
        에이전트가 선택한 action(딕셔너리)을 실행하고 턴을 처리합니다.
        """
        player = self.players[self.current_player_idx]

        # [1단계] 메인 액션 수행
        self._execute_main_action(player, action)
        
        # [2단계] 토큰 상한 처리
        total_gems = sum(player.gems.values())
        if total_gems > 10:
            # 여기서는 액션 딕셔너리에 'discard' 정보가 포함되어 있다고 가정합니다.
            # 예: action = {'type': 'take_diff', 'colors': [...], 'discard': {'red': 1}}
            if 'discard' in action:
                self._execute_discard(player, action['discard'])
            else:
                raise ValueError("토큰이 10개를 초과했는데 버릴 토큰 정보가 없습니다.")

        # [3단계] 귀족 방문 체크
        eligible_nobles = self._get_eligible_nobles(player)
        if eligible_nobles:
            # 2명 이상 충족 시 선택 로직이 필요하지만, 
            # 일단 규칙상 조건을 만족한 첫 번째 귀족을 가져오는 것으로 단순화합니다.
            chosen_noble = eligible_nobles[0] 
            player.nobles.append(chosen_noble)
            player.score += chosen_noble.points
            self.nobles.remove(chosen_noble)

        # 게임 종료 조건 체크 및 턴 넘기기
        self.current_player_idx = (self.current_player_idx + 1) % self.num_players


    # ==========================================
    # 액션 실행 세부 로직
    # ==========================================
    def _execute_main_action(self, player, action):
        action_type = action['type']
        
        if action_type == 'take_diff': # 액션 A (다른 색 최대 3개)
            for color in action['colors']:
                self.bank[color] -= 1
                player.gems[color] += 1
                
        elif action_type == 'take_same': # 액션 B (같은 색 2개)
            color = action['color']
            self.bank[color] -= 2
            player.gems[color] += 2
            
        elif action_type == 'reserve_public': # 액션 C-1 (공개 카드 예약)
            tier, card_id = action['tier'], action['card_id']
            card = next(c for c in self.board[tier] if c.id == card_id)
            self.board[tier].remove(card)
            player.reserved.append(card)
            self._replenish_board(tier)
            self._take_gold_if_available(player)
            
        elif action_type == 'reserve_blind': # 액션 C-2 (블라인드 예약)
            tier = action['tier']
            card = self.decks[tier].pop()
            player.reserved.append(card)
            self._take_gold_if_available(player)
            
        elif action_type == 'purchase': # 액션 D (카드 구매)
            tier, card_id = action['tier'], action['card_id']
            source = action['source'] # 'board' 또는 'reserved'
            
            if source == 'board':
                card = next(c for c in self.board[tier] if c.id == card_id)
                self.board[tier].remove(card)
                self._replenish_board(tier)
            else:
                card = next(c for c in player.reserved if c.id == card_id)
            
            # 플레이어가 토큰을 지불하고, 이를 은행으로 돌려놓음
            paid = player.pay_for_card(card)
            for color, amount in paid.items():
                self.bank[color] += amount
                
        elif action_type == 'pass': # 액션 E (패스)
            pass


    # ==========================================
    # 보조 로직들
    # ==========================================
    def _replenish_board(self, tier):
        """빈 자리에 덱에서 카드를 뽑아 채웁니다. (덱이 비었으면 채우지 않음)"""
        if self.decks[tier]:
            self.board[tier].append(self.decks[tier].pop())

    def _take_gold_if_available(self, player):
        """예약 시 황금 토큰이 남아있다면 1개 가져옵니다."""
        if self.bank['gold'] > 0:
            self.bank['gold'] -= 1
            player.gems['gold'] += 1

    def _execute_discard(self, player, discard_dict):
        """토큰 상한(10개) 초과 시 토큰을 버리고 은행에 반환합니다."""
        for color, amount in discard_dict.items():
            player.gems[color] -= amount
            self.bank[color] += amount

    def _get_eligible_nobles(self, player):
        """현재 플레이어가 방문 조건을 충족한 귀족 목록을 반환합니다."""
        eligible = []
        player_bonuses = player.bonuses
        for noble in self.nobles:
            # 귀족의 모든 요구 조건을 만족하는지 확인
            if all(player_bonuses.get(color, 0) >= req for color, req in noble.requirements.items()):
                eligible.append(noble)
        return eligible

    # ==========================================
    # 상태 내보내기/가져오기 (Serialization)
    # ==========================================
    def export_state(self):
        """현재 게임 상태를 딕셔너리로 내보냅니다."""
        return {
            "num_players": self.num_players,
            "bank": self.bank.copy(),
            "current_player_idx": self.current_player_idx,
            "decks": {t: [c.to_dict() for c in self.decks[t]] for t in [1, 2, 3]},
            "board": {t: [c.to_dict() for c in self.board[t]] for t in [1, 2, 3]},
            "nobles": [n.to_dict() for n in self.nobles],
            "players": [p.to_dict() for p in self.players]
        }
