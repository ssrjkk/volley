# @author ssrjkk | volley
"""Tests for Tracer."""

from volley import Tracer, TraceConfig


class TestTracer:
    """Test Tracer functionality."""

    def test_tracer_default_config(self) -> None:
        """Test Tracer default configuration."""
        tracer = Tracer()
        assert tracer.config.endpoint == "http://localhost:4317"
        assert tracer.config.sample_rate == 1.0
        assert tracer.config.service_name == "volley"

    def test_tracer_custom_config(self) -> None:
        """Test Tracer custom configuration."""
        config = TraceConfig(
            endpoint="http://custom:4317", sample_rate=0.5, service_name="test-service"
        )
        tracer = Tracer(config)
        assert tracer.config.endpoint == "http://custom:4317"
        assert tracer.config.sample_rate == 0.5

    def test_tracer_initial_state(self) -> None:
        """Test Tracer initial state."""
        tracer = Tracer()
        assert tracer.trace_id == ""
        assert tracer._active_span is None
        assert tracer._spans == []

    def test_start_span(self) -> None:
        """Test starting a span."""
        tracer = Tracer()
        tracer.start_span("test_operation")

        assert tracer._active_span is not None
        assert tracer._active_span["name"] == "test_operation"
        assert "trace_id" in tracer._active_span
        assert "span_id" in tracer._active_span
        assert "start_time" in tracer._active_span
        assert tracer.trace_id != ""

    def test_start_span_sets_trace_id(self) -> None:
        """Test first span sets trace_id."""
        tracer = Tracer()
        tracer.start_span("first_span")

        trace_id = tracer.trace_id
        assert trace_id != ""
        assert len(trace_id) == 32

    def test_start_span_reuses_trace_id(self) -> None:
        """Test subsequent spans reuse trace_id."""
        tracer = Tracer()
        tracer.start_span("first_span")
        trace_id_1 = tracer.trace_id

        tracer.end_span()
        tracer.start_span("second_span")
        trace_id_2 = tracer.trace_id

        assert trace_id_1 == trace_id_2

    def test_start_span_ends_previous_span(self) -> None:
        """Test starting new span ends previous one."""
        tracer = Tracer()
        tracer.start_span("span1")
        span1 = tracer._active_span

        tracer.start_span("span2")

        assert span1 in tracer._spans
        assert tracer._active_span is not None
        assert tracer._active_span["name"] == "span2"

    def test_end_span(self) -> None:
        """Test ending a span."""
        tracer = Tracer()
        tracer.start_span("test_span")
        span = tracer._active_span

        tracer.end_span()

        assert tracer._active_span is None
        assert span is not None
        assert span in tracer._spans
        assert "end_time" in span
        start = span["start_time"]
        end = span["end_time"]
        assert isinstance(start, (int, float))
        assert isinstance(end, (int, float))
        assert end >= start

    def test_end_span_without_active(self) -> None:
        """Test ending span when none active."""
        tracer = Tracer()
        tracer.end_span()  # Should not raise

        assert tracer._spans == []

    def test_add_attribute(self) -> None:
        """Test adding attribute to active span."""
        tracer = Tracer()
        tracer.start_span("test_span")
        tracer.add_attribute("key1", "value1")
        tracer.add_attribute("key2", "value2")

        assert tracer._active_span is not None
        attrs = tracer._active_span["attributes"]
        assert isinstance(attrs, dict)
        assert attrs["key1"] == "value1"
        assert attrs["key2"] == "value2"

    def test_add_attribute_without_active_span(self) -> None:
        """Test adding attribute without active span."""
        tracer = Tracer()
        tracer.add_attribute("key", "value")  # Should not raise

        assert tracer._spans == []

    def test_trace_id_property_empty(self) -> None:
        """Test trace_id property when no spans."""
        tracer = Tracer()
        assert tracer.trace_id == ""

    def test_trace_id_property_with_span(self) -> None:
        """Test trace_id property with active span."""
        tracer = Tracer()
        tracer.start_span("test")
        assert tracer.trace_id != ""
        assert len(tracer.trace_id) == 32

    def test_span_id_uniqueness(self) -> None:
        """Test span IDs are unique."""
        tracer = Tracer()
        tracer.start_span("span1")
        assert tracer._active_span is not None
        span1_id = tracer._active_span["span_id"]
        assert isinstance(span1_id, str)

        tracer.end_span()
        tracer.start_span("span2")
        assert tracer._active_span is not None
        span2_id = tracer._active_span["span_id"]
        assert isinstance(span2_id, str)

        assert span1_id != span2_id
        assert len(span1_id) == 16
        assert len(span2_id) == 16

    def test_span_attributes_isolation(self) -> None:
        """Test span attributes are isolated."""
        tracer = Tracer()
        tracer.start_span("span1")
        tracer.add_attribute("key", "value1")
        tracer.end_span()

        tracer.start_span("span2")
        tracer.add_attribute("key", "value2")

        span1 = tracer._spans[0]
        attrs1 = span1["attributes"]
        assert isinstance(attrs1, dict)
        assert tracer._active_span is not None
        attrs2 = tracer._active_span["attributes"]
        assert isinstance(attrs2, dict)

        assert attrs1["key"] == "value1"
        assert attrs2["key"] == "value2"

    def test_multiple_spans_collection(self) -> None:
        """Test collecting multiple spans."""
        tracer = Tracer()

        for i in range(5):
            tracer.start_span(f"span_{i}")
            tracer.add_attribute("index", str(i))
            tracer.end_span()

        assert len(tracer._spans) == 5
        assert tracer._active_span is None

        for i, span in enumerate(tracer._spans):
            assert span["name"] == f"span_{i}"
            attrs = span["attributes"]
            assert isinstance(attrs, dict)
            assert attrs["index"] == str(i)
