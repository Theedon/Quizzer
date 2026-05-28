from src.agent.graph import build_generator_subgraph


def test_subgraph_is_cached():
    sg1 = build_generator_subgraph()
    sg2 = build_generator_subgraph()
    assert sg1 is sg2
