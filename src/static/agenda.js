let sitting_id = parseInt($("#js").attr("sitting_id"));
let post_url = `/pps/be/core/sitting/agenda/${sitting_id}`;
var status = new Map();
var emitter = mitt();
// officials_map 在agenda.html

let ws_link = "";
if (location.protocol !== "https:") {
    // for dev
    ws_link = `ws://${location.hostname}:3227/pps/be/core/sitting/agendaws/${sitting_id}`;
} else {
    ws_link = `wss://${location.hostname}/oj/be/core/sitting/agendaws/${sitting_id}`;
}
var ws = new WebSocket(ws_link);

ws.onopen = (event) => {
    ws.send(
        JSON.stringify({
            action: "connection",
            data: {
                member_id: route.member_id,
                session_id: route.get_session_id(),
                sitting_id: sitting_id,
            },
        })
    );

    send_data(ws, "query", { type: "interpellations" });
    send_data(ws, "query", { type: "impromptu" });
    send_data(ws, "query", { type: "current-agenda" });
};

ws.onmessage = (event) => {
    console.log(event.data);
    let data = JSON.parse(event.data);
    if (data["action"] == "notify" && data["data"]["type"] == "next-agenda") {
        send_data(ws, "query", { type: "current-agenda" });
    }

    if (
        data["action"] == "update" &&
        data["data"]["type"] == "current-agenda"
    ) {
        let agenda = data["data"]["agenda"];
        if (agenda == "text") {
            let text_id = data["data"]["text_id"];
            $(`#${text_id}`).css("background-color", "yellow");
        } else if (agenda == "interpellations") {
            emitter.emit("ws", data);
        } else if (agenda == "proposal-discussion") {
            $("#proposal-discussion").css("background-color", "yellow");
            let bill_id = data["data"]["current_bill_id"];
            $("#collapseProposal")
                .find(`span#${bill_id}`)
                .css("background-color", "yellow");
        } else if (agenda == "impromptu-motion") {
            $("#impromptu-motion").css("background-color", "yellow");
            let index = data["data"]["impromptu_index"];
            $("#collapseImpromptu")
                .find(`#${index}`)
                .css("background-color", "yellow");
        }
    }

    emitter.emit("ws", data);
};

function send_data(ws, action, data) {
    ws.send(
        JSON.stringify({
            action: action,
            data: data,
        })
    );
}

function agenda_event() {
    $("button.start").on("click", function (event) {
        $.post(post_url, {
            reqtype: "sitting-start",
        });

        $("button.stop").removeClass("disabled");
        $("button.pause").removeClass("disabled");
        $(this).addClass("disabled");
    });

    $("button.stop").on("click", (event) => {
        $.post(post_url, {
            reqtype: "sitting-stop",
        });
    });

    $("#durationForm")
        .find("#submit")
        .on("click", (event) => {
            let duration = $("#InputDuration").val();
            if (isNaN(duration)) {
                alert("不要亂輸入");
                return;
            }

            $.post(post_url, {
                reqtype: "sitting-pause",
                duration: duration,
            });
        });
}

function proposal_event() {
    $("#collapseProposal")
        .find("div")
        .each(function (i, i_element) {
            $(i_element)
                .find("button")
                .each(function (j, j_element) {
                    let id = $(this).attr("type");
                    if (id.endsWith("1")) {
                        $(this).on("click", function (event) {
                            without_objection($(this).attr("id"), $(this));
                        });
                    } else if (id.endsWith("2")) {
                        $(this).on("click", function (event) {
                            show_vote_ui($(this).attr("id"), "proposal");
                        });
                    } else if (id.endsWith("3")) {
                        $(this).on("click", function (event) {});
                    }
                });
        });
}

function without_objection(bill_id) {
    send_data(ws, "update", {
        type: "without-objection",
        bill_id: bill_id,
    });
}

function show_vote_ui(bill_id, agenda_type) {
    let UI = $("#UI");
    if (UI.attr("isOpenUI") != "false") {
        return;
    }

    let voteUI = $("#voteUI");
    if (voteUI.css("display") != "none") {
        return;
    }
    ws.send(
        JSON.stringify({
            action: "query",
            data: {
                type: "get-vote-result",
                bill_id: bill_id,
                q_type: agenda_type,
            },
        })
    );

    voteUI.show();
    voteUI.attr("billId", bill_id);
    UI.attr("isOpenUI", "true");
}

function vote_vue(ws, emitter) {
    Vue.createApp({
        data() {
            this.voteUI = $("#voteUI");
            this.UI = $("#UI");
            return {
                vote_option_type: 1,
                custom_option: "",
                options: [
                    { option: "同意", count: 0 },
                    { option: "不同意", count: 0 },
                    { option: "棄權", count: 0 },
                ],
                duration: 60,
                opened: false,
            };
        },
        computed: {
            duration_format() {
                let sec = this.duration % 60;
                if (sec == 0) {
                    sec = "00";
                } else if (sec < 10) {
                    sec = `0${sec}`;
                }

                let minute = parseInt(this.duration / 60);
                return `${minute}:${sec}`;
            },
        },
        methods: {
            add_custom_option() {
                if (
                    this.custom_option == undefined ||
                    this.custom_option == ""
                ) {
                    alert("投票選項不能為空");
                    return;
                }
                this.options.push({
                    option: this.custom_option,
                    count: 0,
                });
                this.custom_option = "";
            },

            init() {
                this.vote_option_type = 1;
                this.custom_option = "";
                this.options = [
                    { option: "同意", count: 0 },
                    { option: "不同意", count: 0 },
                    { option: "棄權", count: 0 },
                ];
                this.duration = 60;
                this.opened = false;
            },

            handle(data) {
                if (
                    !(data["action"] == "update" || data["action"] == "notify")
                ) {
                    return;
                }

                let type = data["data"]["type"];
                if (type == "vote-result") {
                    if (data["data"]["result"] != null) {
                        console.log(data["data"]["result"]);
                        this.duration = 0;
                        this.options = data["data"]["result"];
                    } else {
                        this.init();
                    }
                } else if (type == "update-vote-count") {
                    data["data"]["counts"].forEach((count, idx, _) => {
                        this.options[idx].count = count;
                    });
                } else if (type == "vote-start") {
                    this.timerID = setInterval(this.timer.bind(this), 1000);
                } else if (type == "vote-end") {
                    clearInterval(this.timerID);
                }
            },

            timer() {
                if (this.duration == 0) {
                    return;
                }
                this.duration--;
            },

            start_vote() {
                if (isNaN(this.duration) || this.duration <= 0) {
                    alert("請輸入正確時間");
                    return;
                }
                if (this.options.length == 0) {
                    alert("投票選項不能為空");
                    return;
                }

                send_data(ws, "update", {
                    type: "start-vote",
                    bill_id: this.voteUI.attr("billId"),
                    options: this.options,
                    duration: this.duration,
                    free: this.opened,
                });
            },

            close_ui() {
                this.init();
                this.voteUI.hide();
                this.voteUI.attr("billId", "");
                this.UI.attr("isOpenUI", "false");
            },
        },
        watch: {
            vote_option_type(new_type, old_type) {
                if (new_type == 2 && old_type == 1) {
                    this.options.length = 0;
                } else {
                    this.options = [
                        { option: "同意", count: 0 },
                        { option: "不同意", count: 0 },
                        { option: "棄權", count: 0 },
                    ];
                }
            },
        },
        mounted() {
            emitter.on("ws", this.handle);
        },
        delimiters: ["{", "}"],
    }).mount("#voteUI");
}

function impromptu_vue(ws, emitter) {
    const { createApp } = Vue;
    createApp({
        data() {
            return {
                impromptus: [],
            };
        },
        methods: {
            update(impromptu_list) {
                this.impromptus.length = 0; //  clear list
                impromptu_list.forEach((impromptu) => {
                    this.impromptus.push(impromptu);
                });
            },
            ws_handle(data) {
                if (data["action"] == "update") {
                    let type = data["data"]["type"];
                    if (
                        type == "new-impromptu-motion" ||
                        type == "to-second-motion"
                    ) {
                        this.update(data["data"]["list"]);
                    }
                }
            },

            ui_handle(data) {
                if (data == "query-pre-impromptu") {
                    ws.send(
                        JSON.stringify({
                            action: "query",
                            data: {
                                type: "pre-impromptu",
                            },
                        })
                    );
                }
            },

            start_submit() {
                ws.send(
                    JSON.stringify({
                        action: "update",
                        data: {
                            type: "impromptu-start-submit",
                        },
                    })
                );
            },

            close_submit() {
                ws.send(
                    JSON.stringify({
                        action: "update",
                        data: {
                            type: "impromptu-close-submit",
                        },
                    })
                );
            },

            close_ui() {
                $("#impromptuUI").hide();
                $("#UI").attr("isOpenUI", "false");
            },
        },
        mounted() {
            emitter.on("ws", this.ws_handle);
            emitter.on("ui", this.ui_handle);
        },
        delimiters: ["{", "}"],
    }).mount("#impromptuUI");
}

function interpellation_vue(ws, emitter) {
    const { createApp } = Vue;
    createApp({
        data() {
            return {
                interpellations: [],
            };
        },
        methods: {
            ws_handle(data) {
                if (data["action"] != "update") {
                    return;
                }

                if (data["data"]["type"] == "update-interpellation") {
                    console.log(data["data"]["list"]);
                    this.interpellations = data["data"]["list"];
                }
            },

            ui_handle(data) {
                if (data == "query-interpellation") {
                    ws.send(
                        JSON.stringify({
                            action: "query",
                            data: {
                                type: "interpellations",
                            },
                        })
                    );
                }
            },

            start_submit() {
                ws.send(
                    JSON.stringify({
                        action: "update",
                        data: {
                            type: "interpellation-start-submit",
                        },
                    })
                );
            },

            close_submit() {
                ws.send(
                    JSON.stringify({
                        action: "update",
                        data: {
                            type: "interpellation-close-submit",
                        },
                    })
                );
            },

            close_ui() {
                $("#interpellationUI").hide();
                $("#UI").attr("isOpenUI", "false");
            },
        },
        mounted() {
            emitter.on("ws", this.ws_handle);
            emitter.on("ui", this.ui_handle);
        },
        delimiters: ["{", "}"],
    }).mount("#interpellationUI");
}

function agenda_vue(ws, emitter) {
    Vue.createApp({
        data() {
            this.UI = $("#UI");
            return {
                editable: false,
                interpellations: [],
                impromptus: [],
            };
        },
        methods: {
            show_impromptu_ui() {
                if (this.UI.attr("isOpenUI") != "false") {
                    return;
                }

                let impromptuUI = $("#impromptuUI");
                if (impromptuUI.css("display") != "none") {
                    return;
                }
                impromptuUI.show();
                this.UI.attr("isOpenUI", "true");
                emitter.emit("ui", "query-pre-impromptu");
            },

            vote_ui(event) {
                let target = $(event.target);
                show_vote_ui(target.attr("id"), "impromptu");
            },

            without_objection(event) {
                let target = $(event.target);
                without_objection(target.attr("id"));
            },

            show_interpellation_ui() {
                if (this.UI.attr("isOpenUI") != "false") {
                    return;
                }

                let interpellationUI = $("#interpellationUI");
                if (interpellationUI.css("display") != "none") {
                    return;
                }
                interpellationUI.show();
                this.UI.attr("isOpenUI", "true");
                emitter.emit("ui", "query-interpellation");
            },

            interpellation_timer(event) {
                let target = $(event.target);
                let send_data = {
                    action: "update",
                    data: {},
                };

                if (target.hasClass("timer-start")) {
                    send_data.data["type"] = "interpellation-start";
                } else if (target.hasClass("timer-pause")) {
                    send_data.data["type"] = "interpellation-pause";
                } else if (target.hasClass("timer-keep")) {
                    send_data.data["type"] = "interpellation-keep";
                } else if (target.hasClass("timer-stop")) {
                    send_data.data["type"] = "interpellation-stop";
                }

                send_data.data["idx"] = target.attr("index");

                ws.send(JSON.stringify(send_data));
                ws.send(
                    JSON.stringify({
                        action: "query",
                        data: {
                            type: "interpellations",
                        },
                    })
                );
            },

            ui_handle(data) {},

            ws_handle(data) {
                if (data["action"] != "update") {
                    return;
                }

                if (data["data"]["agenda"] == "interpellations") {
                    let idx = data["data"]["current_idx"];
                    $("#interpellations").css("background-color", "yellow");
                    if (idx >= 0 && idx < this.interpellations.length)
                        this.interpellations[idx]["highlight"] = "yellow";
                }

                if (data["data"]["type"] == "update-interpellation") {
                    console.log(data["data"]["list"]);
                    this.interpellations = data["data"]["list"];
                } else if (data["data"]["type"] == "to-second-motion") {
                    ws.send(
                        JSON.stringify({
                            action: "query",
                            data: {
                                type: "impromptu",
                            },
                        })
                    );
                } else if (data["data"]["type"] == "impromptu") {
                    this.impromptus = data["data"]["list"];
                }
            },

            next_agenda() {
                ws.send(
                    JSON.stringify({
                        action: "update",
                        data: {
                            type: "next-agenda",
                            orders: this.agenda_order,
                        },
                    })
                );
            },

            remove_agenda(event) {
                event.currentTarget.parentElement.remove();
            },

            send_updated_agenda() {
                this.agenda_order = [];
                $("p.agenda-index").each((idx, element) => {
                    this.agenda_order.push(element.getAttribute("index"));
                });

                ws.send(
                    JSON.stringify({
                        action: "update",
                        data: {
                            type: "reorder-agenda",
                            orders: this.agenda_order,
                        },
                    })
                );
            },
        },
        watch: {
            editable(newValue, oldValue) {
                if (newValue == false && oldValue == true) {
                    this.send_updated_agenda();
                }
            },
        },
        mounted() {
            emitter.on("ui", this.ui_handle);
            emitter.on("ws", this.ws_handle);
        },
        updated() {
            emitter.on("ui", this.ui_handle);
        },
        delimiters: ["{", "}"],
    }).mount("#agendaUI");
}

function init() {
    vote_vue(ws, emitter);
    impromptu_vue(ws, emitter);
    interpellation_vue(ws, emitter);
    agenda_vue(ws, emitter);

    agenda_event();
    proposal_event();
}

init();
