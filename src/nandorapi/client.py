# PLANNED USAGE:
#
## Define the client object
#client = nandorapi.client.Client(
#    'some_url',
#    end_conditions=end_conditions,
#    query={'hashtag':'tylenol'},
#    timeouts=1, # An int is interpreted as the number of seconds
#    end_conditions=end_conditions,
#    output=output
#)
#
## To run the scraper, this is all you have to do:
#while client:
#    # This pages through, runs the queries, saves the results, pauses appropriately.
#    client.run()
from nandorapi import tools
import requests

class Client:
    def __init__(
        self,
        url,
        end_conditions: tools.EndConditions,
        pager: tools.Paging,
        query: dict,
        payload: dict | None = None,
        timeout: tools.Timeout | int = tools.Timeout(pause_seconds=15),
        output: tools.Output = tools.Output()
    ):
        self.url = url
        self.end_conditions = end_conditions
        self.pager = pager
        self.query = query
        self.payload = payload
        self.output = output

        if isinstance(timeout, [int | float]):
            timeout = tools.Timeout(pause_seconds=15)

        self.timeout = timeout

        self.still_running = True
    
    def run(self):

        page = next(self.pager)

        if not self.payload:
            header = dict(
                **self.query,
                **page
            )

            r = requests.get(
                self.url,
                headers=header
            )

        else:
            raise NotImplementedError()
        
        self.output.write_bytes(r.content)

        if self.end_conditions.check_if_met():
            self.still_running = False
        
        self.timeout.pause()

    def __bool__(self):
        return self.still_running