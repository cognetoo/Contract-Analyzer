class AgentState:
    def __init__(self):
        self.context = ""                 # accumulated analysis
        self.completed_steps = []         # step + status + notes
        self.missing_points = []          # missing parts
        self.feedback = []                # reflection feedback
        self.iteration = 0
        self.complete = False
