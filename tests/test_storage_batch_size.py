from vrp.storage.batching import rows_per_batch


def test_batch_size_respects_bind_limit():
    assert rows_per_batch(60, 1000) == 500
