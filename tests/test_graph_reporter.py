import unittest
from reporters.graph import GraphReporter
from models import MasterIdentity, IdentityAnchor


class TestGraphReporter(unittest.TestCase):
    def test_graph_construction(self):
        identity = MasterIdentity()
        identity.email.append(IdentityAnchor(value="a@b.com"))
        identity.username.append(IdentityAnchor(value="user1"))

        reporter = GraphReporter()
        reporter.build_from_identity(identity)

        # Subject + 1 email + 1 username = 3 nodes
        self.assertEqual(len(reporter.graph.nodes), 3)
        self.assertEqual(len(reporter.graph.edges), 2)

    def test_louvain(self):
        reporter = GraphReporter()
        # Create two disjoint clusters connected via Subject
        reporter.graph.add_edge("Subject", "A")
        reporter.graph.add_edge("A", "B")
        reporter.graph.add_edge("Subject", "X")
        reporter.graph.add_edge("X", "Y")

        reporter.apply_louvain()
        for node in reporter.graph.nodes:
            self.assertIn("community", reporter.graph.nodes[node])


if __name__ == "__main__":
    unittest.main()
