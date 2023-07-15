let sitting_id = parseInt($("#js").attr("sitting_id"));
let post_url = `/pps/be/core/agenda/${sitting_id}`;
var status = new Map();

let ws_link = "";
if (location.protocol !== "https:") {
    // for dev
    ws_link = `ws://${location.hostname}:3227/pps/be/core/sitting/agendaws/${sitting_id}`;
} else {
    ws_link = `wss://${location.hostname}/oj/be/core/sitting/agendaws/${sitting_id}`;
}
var ws = new WebSocket(ws_link);

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

    $("button.pause").on("click", (event) => {
        $.post(post_url, {
            reqtype: "sitting-pause",
            // time: time,
        });
    });

    $("#nextAgenda").on("click", (event) => {
        $.post(post_url, {
            reqtype: "next-agenda",
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
                    let id = $(this).attr("id");
                    if (id.endsWith("1")) {
                        $(this).on("click", function (event) {
                            without_objection(
                                i.toString() + "-" + id.slice(0, id.length - 2), $(this)
                            );
                        });
                    } else if (id.endsWith("2")) {
                        $(this).on("click", function (event) {
                            vote(
                                i.toString() + "-" + id.slice(0, id.length - 2), $(this)
                            );
                        });
                    } else if (id.endsWith("3")) {
                        $(this).on("click", function (event) {
                        });
                    }
                });
        });
}

function vote_event() {
    let voteUI = $("#voteUI");
    voteUI
        .find("button.close")
        .on("click", function (event) {
            // if
            // $("#voteUI").hide();
        });

    voteUI.find("select").on('change', function(event) {
        
    });
}

function without_objection(bill_index, element) {
    $.post(post_url, {
        reqtype: "without-objection",
        bill_index: bill_index,
    });
}

function vote(bill_index, element) {
    let voteUI = $("#voteUI");
    $("#voteUI").show();


}

function init() {
    agenda_event();
    proposal_event();
    vote_event();
}

init();
