import unittest
from unittest.mock import patch, call
from app.anki import group_existing_notes

class TestGrouping(unittest.TestCase):
    @patch('app.anki.invoke')
    def test_group_existing_notes_success(self, mock_invoke):
        # Setup mocks
        # First call: get_deck_notes -> findNotes
        # Second call: group_existing_notes -> notesInfo
        # Subsequent calls: ensure_deck_exists -> deckNames, createDeck (if needed), changeDeck
        
        # 1. findNotes returns 5 note IDs in unsorted order to verify ascending sorting
        note_ids = [105, 101, 103, 102, 104]
        
        # 2. notesInfo returns note details with cards list
        # note IDs are sorted: 101, 102, 103, 104, 105
        # Index:
        # 0: 101 -> card 201
        # 1: 102 -> card 202
        # 2: 103 -> card 203
        # 3: 104 -> card 204
        # 4: 105 -> card 205
        notes_info_response = [
            {"noteId": 101, "cards": [201]},
            {"noteId": 102, "cards": [202]},
            {"noteId": 103, "cards": [203]},
            {"noteId": 104, "cards": [204]},
            {"noteId": 105, "cards": [205]},
        ]
        
        # Mock responses
        def side_effect(action, **params):
            if action == "findNotes":
                return note_ids
            elif action == "notesInfo":
                # Ensure the notes parameter matches the sorted list [101, 102, 103, 104, 105]
                self.assertEqual(params["notes"], [101, 102, 103, 104, 105])
                return notes_info_response
            elif action == "deckNames":
                # Let's pretend only the parent deck exists
                return ["TestDeck"]
            elif action == "createDeck":
                return None
            elif action == "changeDeck":
                return None
            raise ValueError(f"Unexpected action: {action}")
            
        mock_invoke.side_effect = side_effect
        
        # Call the function with group_size = 2
        # Expected groups (sorted order):
        # Group 1: indices 0, 1 -> cards 201, 202 -> deck 'TestDeck::Group 1'
        # Group 2: indices 2, 3 -> cards 203, 204 -> deck 'TestDeck::Group 2'
        # Group 3: index 4 -> card 205 -> deck 'TestDeck::Group 3'
        
        group_existing_notes("TestDeck", group_size=2)
        
        # Verify deckNames and createDeck/changeDeck invocations
        # Specifically, check the calls to changeDeck
        change_deck_calls = [
            c for c in mock_invoke.call_args_list if c[0][0] == "changeDeck"
        ]
        
        self.assertEqual(len(change_deck_calls), 3)
        
        # First group
        self.assertEqual(change_deck_calls[0], call("changeDeck", cards=[201, 202], deck="TestDeck::Group 1"))
        # Second group
        self.assertEqual(change_deck_calls[1], call("changeDeck", cards=[203, 204], deck="TestDeck::Group 2"))
        # Third group
        self.assertEqual(change_deck_calls[2], call("changeDeck", cards=[205], deck="TestDeck::Group 3"))

    @patch('app.anki.invoke')
    def test_group_existing_notes_empty(self, mock_invoke):
        # findNotes returns empty list
        mock_invoke.return_value = []
        
        group_existing_notes("TestDeck", group_size=2)
        
        # should only call findNotes
        mock_invoke.assert_called_once_with("findNotes", query='deck:"TestDeck"')

if __name__ == "__main__":
    unittest.main()
