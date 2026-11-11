"""Synthetic-only adapter. Adopters must implement their scholarly constraints."""
def validate_records(records, proposal):
    if proposal['scope']['numberedReportCount'] != 0:
        raise ValueError('Synthetic prose fixture has no hadith reports')
