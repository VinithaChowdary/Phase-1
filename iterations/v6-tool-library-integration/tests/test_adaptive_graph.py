import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock pydantic_ai.models.vertexai before importing meta_agent_graph
sys.modules["pydantic_ai.models.vertexai"] = MagicMock()

from meta_agent.meta_agent_graph import evaluate_code, route_evaluation, AgentState
from meta_agent.evaluator_agent import ConfidenceScore

class TestAdaptiveGraph(unittest.IsolatedAsyncioTestCase):

    async def test_evaluate_code_high_confidence(self):
        # Mock state
        state = {
            "messages": [], 
            "refinement_count": 0
        }
        
        # Mock evaluator response
        mock_score = ConfidenceScore(
            score=0.9, 
            reasoning="Good code", 
            needs_refinement=False, 
            refinement_targets=[]
        )
        
        # Mock result object that matches Pydantic AI result structure
        mock_result = MagicMock()
        mock_result.data = mock_score
        
        with patch('meta_agent.meta_agent_graph.evaluator_agent.run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            result = await evaluate_code(state)
            
            self.assertEqual(result['confidence_score'], 0.9)
            self.assertEqual(result['refinement_count'], 0)
            self.assertFalse(result['refinement_targets'])

    async def test_evaluate_code_low_confidence(self):
        state = {
            "messages": [], 
            "refinement_count": 0
        }
        
        mock_score = ConfidenceScore(
            score=0.6, 
            reasoning="Bad code", 
            needs_refinement=True, 
            refinement_targets=["prompt"]
        )
        
        mock_result = MagicMock()
        mock_result.data = mock_score
        
        with patch('meta_agent.meta_agent_graph.evaluator_agent.run', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            
            result = await evaluate_code(state)
            
            self.assertEqual(result['confidence_score'], 0.6)
            self.assertEqual(result['refinement_count'], 1) # Should increment
            self.assertEqual(result['refinement_targets'], ["prompt"])

    def test_route_evaluation_refine(self):
        state = {
            "confidence_score": 0.5,
            "refinement_count": 1,
            "refinement_targets": ["prompt", "tools"]
        }
        
        next_nodes = route_evaluation(state)
        self.assertIn("refine_prompt", next_nodes)
        self.assertIn("refine_tools", next_nodes)

    def test_route_evaluation_give_up(self):
        state = {
            "confidence_score": 0.5,
            "refinement_count": 4, # Too many retries
            "refinement_targets": ["prompt"]
        }
        
        next_node = route_evaluation(state)
        self.assertEqual(next_node, "get_next_user_message")

    def test_route_evaluation_success(self):
        state = {
            "confidence_score": 0.9,
            "refinement_count": 1,
            "refinement_targets": []
        }
        
        next_node = route_evaluation(state)
        self.assertEqual(next_node, "get_next_user_message")

if __name__ == '__main__':
    unittest.main()
