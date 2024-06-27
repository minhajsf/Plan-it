import unittest
import GCal_Manager
from unittest.mock import patch


class TestCalendar(unittest.TestCase):

    # python -m unittest test_calendar.py
    @patch('builtins.input', side_effect=['Create', 'Set up a meeting with ' +
                                          'Brooke tomorrow at 5PM'])
    def test_create_1(self, mock_input):
        self.assertEqual(GCal_Manager.main(), "Meeting with Brooke")

    @patch('builtins.input', side_effect=['Create', 'I have a meeting with ' +
                                          'John at 5PM'])
    def test_create_2(self, mock_input):
        self.assertEqual(GCal_Manager.main(), "Meeting with John")

    @patch('builtins.input', side_effect=['Update', 'Meeting with Brooke',
                                          "I'd like to change the title to" +
                                          " 'Interview with Brooke'"])
    def test_update(self, mock_input):
        self.assertEqual(GCal_Manager.main(), "Interview with Brooke")

    @patch('builtins.input', side_effect=['Remove', 'Interview with Brooke',
                                          'y'])
    def test_remove_1(self, mock_input):
        self.assertEqual(GCal_Manager.main(), 'Interview with Brooke')

    @patch('builtins.input', side_effect=['Remove', 'Meeting with John', 'n'])
    def test_remove_2(self, mock_input):
        self.assertEqual(GCal_Manager.main(), None)


if __name__ == '__main__':
    unittest.main()

