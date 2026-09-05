from nozle.identifiers import create_transaction_id


class EventsNamespace:
    def create_transaction_id(self) -> str:
        return create_transaction_id()
