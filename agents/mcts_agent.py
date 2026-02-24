import random
import math
from splender.game import GameState

class MCTSNode:
    def __init__(self, state_dict, parent=None, action=None):
        self.state_dict = state_dict  # 가상 평행우주의 게임 상태 (JSON 딕셔너리)
        self.parent = parent          # 부모 노드
        self.action = action          # 이 우주로 오기 위해 취한 행동
        self.children = []            # 파생된 미래의 우주들
        self.untried_actions = None   # 아직 시도해보지 않은 행동들
        self.visits = 0               # 이 우주를 방문한 횟수
        self.wins = 0                 # 이 우주에서 승리한 횟수

class MCTSAgent:
    def __init__(self, player_idx, iterations=100):
        self.player_idx = player_idx
        self.iterations = iterations  # 생각할 시간 (시뮬레이션 반복 횟수)

    def get_action(self, state):
        # 1. 현재 진짜 게임판의 상태를 복제하여 뿌리(Root) 노드 생성
        root_state_dict = state.export_state()
        root_node = MCTSNode(root_state_dict)
        
        # 임시 게임 엔진 (가상 시뮬레이션용)
        sim_game = GameState.import_state(root_state_dict)
        root_node.untried_actions = sim_game.get_legal_actions()

        # 정해진 횟수만큼 평행우주 탐색 반복
        for _ in range(self.iterations):
            node = root_node
            sim_game = GameState.import_state(node.state_dict)

            # [1] Selection (선택) & [2] Expansion (확장)
            # 자식이 있고 시도 안 한 액션이 없다면, 가장 유망한 자식으로 내려감 (UCT 알고리즘)
            while not node.untried_actions and node.children:
                node = self._select_best_child(node)
                sim_game.step(node.action)
                
            # 시도 안 한 액션이 있다면 하나 골라서 우주(Node)를 확장함
            if node.untried_actions:
                action = random.choice(node.untried_actions)
                node.untried_actions.remove(action)
                
                sim_game.step(action)
                new_state_dict = sim_game.export_state()
                
                child_node = MCTSNode(new_state_dict, parent=node, action=action)
                child_node.untried_actions = sim_game.get_legal_actions()
                node.children.append(child_node)
                node = child_node

            # [3] Simulation (시뮬레이션 - 끝날 때까지 막 둬보기)
            while not sim_game.is_game_over:
                # 안전장치: 너무 오래 걸리면 중단
                if not sim_game.get_legal_actions(): break
                random_action = random.choice(sim_game.get_legal_actions())
                sim_game.step(random_action)

            # [4] Backpropagation (역전파 - 결과 기록하기)
            # 내가 이겼으면 1점, 졌으면 0점
            win = 1 if sim_game.winner and sim_game.winner.id == self.player_idx else 0
            
            while node is not None:
                node.visits += 1
                node.wins += win
                node = node.parent

        # 탐색이 모두 끝나면, 가장 많이 방문한(가장 확실한) 행동을 반환
        best_child = max(root_node.children, key=lambda c: c.visits)
        return best_child.action

    def _select_best_child(self, node):
        """UCT (Upper Confidence Bound) 공식을 사용하여 승률+탐험 가치가 가장 높은 자식을 고릅니다."""
        best_score = -1
        best_child = None
        for child in node.children:
            # 승률 (Exploitation) + 탐험 보너스 (Exploration)
            win_rate = child.wins / child.visits
            exploration = math.sqrt(2 * math.log(node.visits) / child.visits)
            uct_score = win_rate + exploration
            
            if uct_score > best_score:
                best_score = uct_score
                best_child = child
        return best_child
