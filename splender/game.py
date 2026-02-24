import random
import itertools
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
    # 턴 진행 파이프라인
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
    def get_legal_actions(self):
        """현재 턴의 플레이어가 할 수 있는 모든 유효한 행동 리스트를 반환합니다."""
        legal_actions = []
        player = self.players[self.current_player_idx]
        colors = ['white', 'blue', 'green', 'red', 'black']

        # --------------------------------------------------
        # [1] 액션 D: 카드 구매 (가장 우선순위가 높은 행동)
        # --------------------------------------------------
        # 보드에 깔린 카드 확인
        for tier, cards in self.board.items():
            for card in cards:
                if player.can_buy(card):
                    legal_actions.append({
                        'type': 'purchase', 'tier': tier, 'card_id': card.id, 'source': 'board'
                    })
        # 예약한 카드 확인
        for card in player.reserved:
            if player.can_buy(card):
                legal_actions.append({
                    'type': 'purchase', 'tier': card.tier, 'card_id': card.id, 'source': 'reserved'
                })

        # --------------------------------------------------
        # [2] 액션 C: 카드 예약 (예약 슬롯 3장 미만일 때만)
        # --------------------------------------------------
        if len(player.reserved) < 3:
            # C-1. 보드 공개 카드 예약
            for tier, cards in self.board.items():
                for card in cards:
                    # 예약 시 황금 토큰을 받는 엣지 케이스는 step()에서 처리되므로 여기선 행동만 정의
                    legal_actions.append({'type': 'reserve_public', 'tier': tier, 'card_id': card.id})
            
            # C-2. 블라인드 예약 (해당 레벨 덱이 비어있지 않을 때만)
            for tier, deck in self.decks.items():
                if len(deck) > 0:
                    legal_actions.append({'type': 'reserve_blind', 'tier': tier})

        # --------------------------------------------------
        # [3] 액션 A & B: 보석 가져오기 (토큰 10개 초과 시 반납 조합 포함)
        # --------------------------------------------------
        available_colors = [c for c in colors if self.bank[c] > 0]
        
        # 액션 A: 서로 다른 색 1~3개 가져오기 (자발적 1, 2개 선택 허용)
        # itertools.combinations를 통해 1개, 2개, 3개 고르는 모든 부분집합 생성
        take_diff_combos = []
        max_take = min(3, len(available_colors))
        for i in range(1, max_take + 1):
            take_diff_combos.extend(list(itertools.combinations(available_colors, i)))
            
        for combo in take_diff_combos: # combo 예: ('red', 'blue')
            legal_actions.extend(self._create_take_actions_with_discard(player, 'take_diff', list(combo)))

        # 액션 B: 같은 색 2개 가져오기 (은행에 4개 이상 있을 때만)
        for color in colors:
            if self.bank[color] >= 4:
                legal_actions.extend(self._create_take_actions_with_discard(player, 'take_same', color))

        # --------------------------------------------------
        # [4] 액션 E: 패스 (아무것도 할 수 없을 때의 안전망)
        # --------------------------------------------------
        if not legal_actions:
            legal_actions.append({'type': 'pass'})

        return legal_actions

    # ==========================================
    # 버릴 토큰의 '경우의 수'를 계산해주는 마법의 보조 함수
    # ==========================================
    def _create_take_actions_with_discard(self, player, action_type, take_data):
        """
        토큰을 가져왔을 때 10개가 넘으면, 버릴 수 있는 모든 토큰 조합을 계산하여
        각각을 독립된 액션으로 쪼개서 반환합니다.
        """
        actions = []
        
        # 가상으로 토큰을 받았을 때의 내 인벤토리 상태 계산
        temp_gems = player.gems.copy()
        if action_type == 'take_diff':
            for c in take_data: temp_gems[c] += 1
        elif action_type == 'take_same':
            temp_gems[take_data] += 2
            
        total_after_take = sum(temp_gems.values())
        discard_count = total_after_take - 10
        
        # 기본 액션 뼈대
        base_action = {'type': action_type}
        if action_type == 'take_diff': base_action['colors'] = take_data
        else: base_action['color'] = take_data

        if discard_count <= 0:
            # 버릴 필요가 없으면 그냥 액션 하나만 추가
            actions.append(base_action)
        else:
            # 버려야 한다면, 현재 가진 토큰(temp_gems) 중 discard_count 개수만큼 뽑는 모든 조합 계산
            # 예: ['red', 'red', 'blue', 'gold'] 뭉치에서 2개를 뽑는 조합
            gem_pool = []
            for color, count in temp_gems.items():
                gem_pool.extend([color] * count)
                
            # 중복 제거된 버리기 조합 (set 활용)
            discard_combos = set(itertools.combinations(gem_pool, discard_count))
            
            for d_combo in discard_combos:
                discard_dict = {c: 0 for c in ['white', 'blue', 'green', 'red', 'black', 'gold']}
                for c in d_combo:
                    discard_dict[c] += 1
                    
                # 버릴 토큰 정보가 추가된 새로운 액션 생성
                new_action = base_action.copy()
                new_action['discard'] = discard_dict
                actions.append(new_action)
                
        return actions
