from vrp.storage.batching import chunks


def test_chunks_preserve_input_order():
    assert list(chunks([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]
