import random
import itertools
from .player import Player
from .components import Card, Noble

COLORS = ['white', 'blue', 'green', 'red', 'black']

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

        # 4. 게임 종료 판정용 플래그
        self.is_last_round = False   # 누군가 15점 이상 → 해당 라운드 끝까지 진행
        self.is_game_over = False    # 라운드가 완전히 끝나서 승자가 결정됨
        self.winner = None           # 승자 Player 객체 (동점 시 카드 적은 쪽)

    # ==========================================
    # 게임 초기화
    # ==========================================
    def reset(self, all_cards, all_nobles):
        """
        게임을 초기 상태로 세팅합니다. (외부에서 전체 카드/귀족 리스트를 주입)
        여러 번 호출해도 안전하도록 모든 상태를 완전 초기화합니다.
        """
        # --- 전체 상태 초기화 ---
        gem_counts = {2: 4, 3: 5, 4: 7}[self.num_players]
        self.bank = {
            'white': gem_counts, 'blue': gem_counts, 'green': gem_counts,
            'red': gem_counts, 'black': gem_counts, 'gold': 5
        }
        self.players = [Player(i) for i in range(self.num_players)]
        self.current_player_idx = 0
        self.decks = {1: [], 2: [], 3: []}
        self.board = {1: [], 2: [], 3: []}
        self.nobles = []
        self.is_last_round = False
        self.is_game_over = False
        self.winner = None

        # --- 카드 분류 및 셔플 ---
        for card in all_cards:
            self.decks[card.tier].append(card)
            
        for tier in self.decks:
            random.shuffle(self.decks[tier])
            for _ in range(4):
                if self.decks[tier]:
                    self.board[tier].append(self.decks[tier].pop())
                    
        # --- 귀족 셔플 및 세팅 (인원수 + 1) ---
        nobles_copy = list(all_nobles)
        random.shuffle(nobles_copy)
        self.nobles = nobles_copy[:self.num_players + 1]

    # ==========================================
    # 턴 진행 파이프라인
    # ==========================================
    def step(self, action):
        """
        에이전트가 선택한 action(딕셔너리)을 실행하고 턴을 처리합니다.
        
        Returns:
            dict: {
                "game_over": bool,
                "winner": Player or None,
                "noble_gained": Noble or None
            }
        """
        if self.is_game_over:
            raise RuntimeError("게임이 이미 종료되었습니다.")

        player = self.players[self.current_player_idx]
        step_info = {"game_over": False, "winner": None, "noble_gained": None}

        # [1단계] 메인 액션 수행
        self._execute_main_action(player, action)
        
        # [2단계] 토큰 상한 처리
        total_gems = sum(player.gems.values())
        if total_gems > 10:
            if 'discard' in action:
                self._execute_discard(player, action['discard'])
            else:
                raise ValueError("토큰이 10개를 초과했는데 버릴 토큰 정보가 없습니다.")

        # [3단계] 귀족 방문 체크
        # 규칙: 조건을 동시에 만족하는 귀족이 여러 명이면 첫 번째를 자동 선택합니다.
        #       (모든 귀족은 3점으로 동일하므로 전략적 차이 없음)
        eligible_nobles = self._get_eligible_nobles(player)
        if eligible_nobles:
            chosen_noble = eligible_nobles[0]
            player.nobles.append(chosen_noble)
            player.score += chosen_noble.points
            self.nobles.remove(chosen_noble)
            step_info["noble_gained"] = chosen_noble

        # [4단계] 게임 종료 판정
        if player.score >= 15:
            self.is_last_round = True

        # 턴 넘기기
        self.current_player_idx = (self.current_player_idx + 1) % self.num_players

        # 라운드 종료 체크: 마지막 라운드가 진행 중이고, 0번 플레이어 차례로 돌아왔으면
        # → 모든 플레이어가 동일한 턴 수를 수행했으므로 게임 종료
        if self.is_last_round and self.current_player_idx == 0:
            self.is_game_over = True
            self.winner = self._determine_winner()
            step_info["game_over"] = True
            step_info["winner"] = self.winner

        return step_info

    def _determine_winner(self):
        """
        게임 종료 시 승자를 결정합니다.
        규칙: 최고 점수 → 동점 시 구매한 카드 수가 적은 쪽이 승리
        """
        candidates = sorted(
            self.players,
            key=lambda p: (-p.score, len(p.cards))
        )
        return candidates[0]

    # ==========================================
    # 액션 실행 세부 로직
    # ==========================================
    def _execute_main_action(self, player, action):
        action_type = action['type']
        
        if action_type == 'take_diff':
            for color in action['colors']:
                self.bank[color] -= 1
                player.gems[color] += 1
                
        elif action_type == 'take_same':
            color = action['color']
            self.bank[color] -= 2
            player.gems[color] += 2
            
        elif action_type == 'reserve_public':
            tier, card_id = action['tier'], action['card_id']
            card = next(c for c in self.board[tier] if c.id == card_id)
            self.board[tier].remove(card)
            player.reserved.append(card)
            self._replenish_board(tier)
            self._take_gold_if_available(player)
            
        elif action_type == 'reserve_blind':
            tier = action['tier']
            if not self.decks[tier]:
                raise ValueError(f"Tier {tier} 덱이 비어있어 블라인드 예약을 할 수 없습니다.")
            card = self.decks[tier].pop()
            player.reserved.append(card)
            self._take_gold_if_available(player)
            
        elif action_type == 'purchase':
            tier, card_id = action['tier'], action['card_id']
            source = action['source']
            
            if source == 'board':
                card = next(c for c in self.board[tier] if c.id == card_id)
                self.board[tier].remove(card)
                self._replenish_board(tier)
            else:  # 'reserved'
                card = next(c for c in player.reserved if c.id == card_id)
                player.reserved.remove(card)
            
            # 토큰 지불 (pay_for_card는 토큰 차감만 담당)
            paid = player.pay_for_card(card)
            for color, amount in paid.items():
                self.bank[color] += amount

            # 카드 획득 및 점수 갱신은 GameState가 담당
            player.cards.append(card)
            player.score += card.points
                
        elif action_type == 'pass':
            pass

    # ==========================================
    # 보조 로직들
    # ==========================================
    def _replenish_board(self, tier):
        """빈 자리에 덱에서 카드를 뽑아 채웁니다."""
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
            if all(player_bonuses.get(color, 0) >= req
                   for color, req in noble.requirements.items()):
                eligible.append(noble)
        return eligible

    # ==========================================
    # 유효한 행동 리스트 생성
    # ==========================================
    def get_legal_actions(self):
        """현재 턴의 플레이어가 할 수 있는 모든 유효한 행동 리스트를 반환합니다."""
        legal_actions = []
        player = self.players[self.current_player_idx]

        # --------------------------------------------------
        # [1] 액션 D: 카드 구매
        # --------------------------------------------------
        for tier, cards in self.board.items():
            for card in cards:
                if player.can_buy(card):
                    legal_actions.append({
                        'type': 'purchase', 'tier': tier,
                        'card_id': card.id, 'source': 'board'
                    })
        for card in player.reserved:
            if player.can_buy(card):
                legal_actions.append({
                    'type': 'purchase', 'tier': card.tier,
                    'card_id': card.id, 'source': 'reserved'
                })

        # --------------------------------------------------
        # [2] 액션 C: 카드 예약 (예약 슬롯 3장 미만일 때만)
        #     예약 시 황금 토큰을 받을 수 있으므로 10개 초과 시 디스카드 필요
        # --------------------------------------------------
        if len(player.reserved) < 3:
            # 예약 시 황금 토큰을 받을지 여부
            gains_gold = self.bank['gold'] > 0
            
            for tier, cards in self.board.items():
                for card in cards:
                    base = {'type': 'reserve_public', 'tier': tier, 'card_id': card.id}
                    legal_actions.extend(
                        self._build_reserve_actions_with_discard(player, base, gains_gold)
                    )
            for tier, deck in self.decks.items():
                if len(deck) > 0:
                    base = {'type': 'reserve_blind', 'tier': tier}
                    legal_actions.extend(
                        self._build_reserve_actions_with_discard(player, base, gains_gold)
                    )

        # --------------------------------------------------
        # [3] 액션 A & B: 보석 가져오기
        # --------------------------------------------------
        available_colors = [c for c in COLORS if self.bank[c] > 0]
        
        # 액션 A: 서로 다른 색 1~3개 가져오기
        max_take = min(3, len(available_colors))
        for i in range(1, max_take + 1):
            for combo in itertools.combinations(available_colors, i):
                legal_actions.extend(
                    self._build_take_actions_with_discard(player, 'take_diff', list(combo))
                )

        # 액션 B: 같은 색 2개 가져오기 (은행에 4개 이상일 때만)
        for color in COLORS:
            if self.bank[color] >= 4:
                legal_actions.extend(
                    self._build_take_actions_with_discard(player, 'take_same', color)
                )

        # --------------------------------------------------
        # [4] 액션 E: 패스
        # --------------------------------------------------
        if not legal_actions:
            legal_actions.append({'type': 'pass'})

        return legal_actions

    # ==========================================
    # DFS 기반 디스카드 조합 생성 (조합 폭발 해결)
    # ==========================================
    @staticmethod
    def _generate_discard_combos(gems_available, discard_count):
        """
        '각 색상별로 몇 개씩 버릴 것인가?'를 DFS로 탐색하여
        중복 없는 유효한 조합만 생성합니다.
        
        Args:
            gems_available: dict - 현재 보유 토큰 (예: {'white': 2, 'red': 3, ...})
            discard_count: int - 버려야 하는 토큰 총 수
            
        Yields:
            dict - 색상별 버릴 수량 (예: {'white': 1, 'red': 1, ...})
        """
        all_colors = ['white', 'blue', 'green', 'red', 'black', 'gold']
        # 실제로 토큰이 있는 색상만 추림
        active_colors = [c for c in all_colors if gems_available.get(c, 0) > 0]
        
        def dfs(idx, remaining, current_combo):
            if remaining == 0:
                # 버릴 토큰을 모두 배정 완료 → 결과 산출
                result = {c: 0 for c in all_colors}
                for c, n in current_combo:
                    result[c] = n
                yield result
                return
            if idx >= len(active_colors):
                # 더 이상 배정할 색상이 없는데 remaining > 0 → 실패
                return
                
            color = active_colors[idx]
            max_discard = min(gems_available[color], remaining)
            
            # 현재 색상에서 0개 ~ max_discard개를 버리는 각 경우를 탐색
            for n in range(max_discard + 1):
                yield from dfs(idx + 1, remaining - n, current_combo + [(color, n)])
        
        yield from dfs(0, discard_count, [])

    def _build_reserve_actions_with_discard(self, player, base_action, gains_gold):
        """
        예약 액션에서 황금 토큰을 받아 10개를 초과할 경우
        디스카드 조합을 붙여 반환합니다.
        """
        if not gains_gold:
            return [base_action]
        
        temp_gems = player.gems.copy()
        temp_gems['gold'] += 1
        total = sum(temp_gems.values())
        discard_count = total - 10
        
        if discard_count <= 0:
            return [base_action]
        
        actions = []
        for discard_dict in self._generate_discard_combos(temp_gems, discard_count):
            new_action = base_action.copy()
            new_action['discard'] = discard_dict
            actions.append(new_action)
        return actions

    def _build_take_actions_with_discard(self, player, action_type, take_data):
        """
        토큰을 가져왔을 때 10개가 넘으면, DFS로 유효한 디스카드 조합을 생성하여
        각각을 독립된 액션으로 반환합니다.
        """
        actions = []
        
        # 가상으로 토큰을 받았을 때의 인벤토리 상태 계산
        temp_gems = player.gems.copy()
        if action_type == 'take_diff':
            for c in take_data:
                temp_gems[c] += 1
        elif action_type == 'take_same':
            temp_gems[take_data] += 2
            
        total_after_take = sum(temp_gems.values())
        discard_count = total_after_take - 10
        
        # 기본 액션 뼈대
        base_action = {'type': action_type}
        if action_type == 'take_diff':
            base_action['colors'] = take_data
        else:
            base_action['color'] = take_data

        if discard_count <= 0:
            actions.append(base_action)
        else:
            for discard_dict in self._generate_discard_combos(temp_gems, discard_count):
                new_action = base_action.copy()
                new_action['discard'] = discard_dict
                actions.append(new_action)
                
        return actions

    # ==========================================
    # 상태 직렬화 / 역직렬화
    # ==========================================
    def export_state(self):
        """
        현재 게임 상태를 JSON-safe 딕셔너리로 내보냅니다.
        (내부 int 키 → 문자열 키로 변환)
        """
        return {
            "num_players": self.num_players,
            "bank": self.bank.copy(),
            "current_player_idx": self.current_player_idx,
            "decks": {str(t): [c.to_dict() for c in self.decks[t]] for t in [1, 2, 3]},
            "board": {str(t): [c.to_dict() for c in self.board[t]] for t in [1, 2, 3]},
            "nobles": [n.to_dict() for n in self.nobles],
            "players": [p.to_dict() for p in self.players],
            "is_last_round": self.is_last_round,
            "is_game_over": self.is_game_over,
        }

    @classmethod
    def import_state(cls, data):
        """
        export_state()로 내보낸 딕셔너리로부터 GameState를 완전히 복원합니다.
        (문자열 키 → 내부 int 키로 변환)
        """
        num_players = data["num_players"]
        gs = cls.__new__(cls)  # __init__ 우회하여 빈 껍데기 생성
        
        gs.num_players = num_players
        gs.bank = data["bank"].copy()
        gs.current_player_idx = data["current_player_idx"]
        
        # 문자열 키 → int 키 변환
        gs.decks = {
            int(t): [Card.from_dict(c) for c in cards]
            for t, cards in data["decks"].items()
        }
        gs.board = {
            int(t): [Card.from_dict(c) for c in cards]
            for t, cards in data["board"].items()
        }
        
        gs.nobles = [Noble.from_dict(n) for n in data["nobles"]]
        gs.players = [Player.from_dict(p) for p in data["players"]]
        gs.is_last_round = data.get("is_last_round", False)
        gs.is_game_over = data.get("is_game_over", False)
        gs.winner = None  # winner는 is_game_over 시 _determine_winner()로 재계산 가능
        
        if gs.is_game_over:
            gs.winner = gs._determine_winner()
        
        return gs
