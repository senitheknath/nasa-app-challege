from test_app import demo, topic


def test_priorities_survive_navigation():
    a = demo()
    topic(a, "Rotation comparison")
    a.slider[0].set_value(70).run()
    topic(a, "Downloads")
    assert a.session_state["weights"]["temperature"] == 70
    topic(a, "Climate history")
    topic(a, "Rotation comparison")
    assert a.slider[0].value == 70 and not a.exception
