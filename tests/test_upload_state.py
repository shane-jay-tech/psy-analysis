"""同名文件替换与安全提交测试。"""

from src.ui.upload_state import commit_loaded_dataset, uploaded_file_identity


class FakeUpload:
    def __init__(self, data: bytes, *, name="data.csv", file_id=None):
        self._data = data
        self.name = name
        self.size = len(data)
        self.file_id = file_id

    def getbuffer(self):
        return memoryview(self._data)


def test_same_name_and_size_with_different_file_id_is_a_replacement():
    first = FakeUpload(b"a,b\n1,2", file_id="first")
    second = FakeUpload(b"a,b\n3,4", file_id="second")
    assert uploaded_file_identity(first) != uploaded_file_identity(second)


def test_identity_falls_back_to_content_hash():
    first = FakeUpload(b"one")
    second = FakeUpload(b"two")
    assert uploaded_file_identity(first) != uploaded_file_identity(second)


def test_commit_replaces_dataset_only_after_caller_has_validated_everything():
    old_df = object()
    new_df = object()
    state = {
        "df": old_df,
        "analysis_output": {"old": True},
        "plan": object(),
        "_upload_error": "old error",
    }
    identity = ("data.csv", 10, "new")
    commit_loaded_dataset(
        state,
        dataframe=new_df,
        meta={"rows": 1},
        inspector={"x": {}},
        file_name="data.csv",
        identity=identity,
    )
    assert state["df"] is new_df
    assert state["analysis_output"] is None
    assert state["plan"] is None
    assert state["_uploaded_file_identity"] == identity
    assert "_upload_error" not in state
