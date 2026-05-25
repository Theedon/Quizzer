from src.agent.graph import _get_graph, _get_subgraph


def test_subgraph_is_cached():
    sg1 = _get_subgraph()
    sg2 = _get_subgraph()
    assert sg1 is sg2


def test_main_graph_is_cached():
    g1 = _get_graph()
    g2 = _get_graph()
    assert g1 is g2
