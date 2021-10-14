(function() {

function map_setup(maps) {

    var map_names = new Set();
    var n_topics = {}
    var map_data = {}

    var spinner_html =
        `<div class="d-flex justify-content-center mt-5">
            <div class="spinner-border align-center mt-5" role="status">
                <span class="sr-only">Loading...</span>
            </div>
         </div>`;

    maps.forEach(
        function (map, index) {
            map_names.add(map["name"]);

            if (map["name"] in n_topics) {
                n_topics[map["name"]].add(map["num_topics"]);
            }
            else {
                n_topics[map["name"]] = new Set([map["num_topics"]]);
            }

            map_data[[map["name"], map["num_topics"]]] = map["data"];
        }
    );

    var map_names = Array.from(map_names).sort();

    map_names.forEach(
        function (map_name, index) {

            var html = `<option value="${map_name}">${map_name}</option>`;

            $("#map-select").append($(html));
        }
    );

    function updateNTopicSelect() {

        var selected_map = $("#map-select" ).val();

        $("#ntopic-select").html("");
        n_topics[selected_map].forEach(
            function(n_top, index) {

                var html = `<option value=${n_top}>${n_top}</option>`;

                $("#ntopic-select").append($(html));
            }
        );
    }

    var vis = null;
    var map_name = null;

    var request_counter=0;

    function make_doc_list(topic_docs) {

        request_counter += 1;

        (function(counter_at_request) {

            var search_id = $("#search-for").val().match(/Q[0-9]+/);

            $("#doc-list").html(spinner_html);

            function triggerNextDoc (meta_info) {

                if (topic_docs.length <= 0) return;
                if (counter_at_request < request_counter) return;

                var next_doc = topic_docs.shift();

                var url="https://digital.staatsbibliothek-berlin.de/werkansicht?PPN=PPN" + next_doc;

                var meta = meta_info[next_doc];

                var author="";

                if ((meta.name0_displayForm != "None") && (meta.name0_role_roleTerm != "fnd")) {
                    author = `; ${meta.name0_displayForm}`;
                }
                else if (meta["originInfo-publication0_publisher"] != "None") {
                    author = `; ${meta["originInfo-publication0_publisher"]}`;
                }

                var search_params = ""
                if (search_id != null) search_params = `&search_id=${search_id}`;

                var item = `
                    <li class="list-group-item text-left" id="doc-list-PPN${next_doc}">
                        <a href="${url}" target="_blank" rel="noopener noreferrer"> ${meta.titleInfo_title} </a> ${author}
                        <a class="btn btn-info btn-sm ml-3"
                            href="index.html?ppn=${next_doc}&model_id=precomputed&el_model_id=precomputed&task=ner${search_params}"
                            target="_blank" rel="noopener noreferrer">NER+EL</a>
                    </li>`;

                $("#doc-list").append(item);

                (function(ppn) {
                    $.get("images/ppn/" + ppn,
                        function (result) {

                            if (result.length == 0) return;

                            var image_button = `
                                <a class="btn btn-info btn-sm ml-3"
                                    href="images/search.html?ids=${result.ids}"
                                    target="_blank" rel="noopener noreferrer">
                                    Graphical Objects (${result.ids.length})
                                </a>
                            `;

                            $("#doc-list-" + ppn).append(image_button);
                        }
                    ).always(
                        function() {
                            triggerNextDoc(meta_info);
                        }
                    );
                })("PPN" + next_doc);
            }

            let post_data = { "ppns" : topic_docs };

            $.ajax({
                    url:  "meta_data",
                    data: JSON.stringify(post_data),
                    type: 'POST',
                    contentType: "application/json",
                    success:
                        function(result) {
                            $("#doc-list").html("");

                            triggerNextDoc(result);
                        },
                    error:
                        function(error) {
                            $("#doc-list").html("Not available.");
                        }
                }
            );

        })(request_counter);
    }

    var topic_num = 0;

    function get_docs(order_by) {

        if (topic_num == 0) return;

        if (order_by.length > 0) order_by = "/" + order_by;

        $.get("topic_docs/" + map_name + "/" + topic_num + order_by, make_doc_list);
    }

    function updateLDAVis() {

        history.pushState(null, "Query", location.origin + location.pathname);

        $("#chart").html("");
        $("#doc-list").html("");
        $("#mds").html("<h6 id=\"mds-heading\" class=\"mt-2 mb-0\"></h6>");
        $("svg").remove();

        var selected_map = $("#map-select" ).val();

        var n_topics = $("#ntopic-select" ).val();
        map_name = map_data[[selected_map,n_topics]]

        LDAvis("topic_models/" + map_name,
            function(vis) {

                (function(term_on, term_off, topic_click, topic_off, state_url) {

                    function update_on_search_input () {

                        var val = $("#search-for").val();

                        if (val == "") {
                            term_off(null);
                            get_docs("");

                            vis.state_save(true);
                            return;
                        }

                        if($('#suggestions option').filter(
                            function(){
                                return this.value.toUpperCase() === val.toUpperCase();
                            }).length)
                        {
                            vis.term_hover(val);
                            get_docs(val);
                        }
                    }

                     $("#search-for").on('input', update_on_search_input);

                     vis.term_on =
                        function(termElem) {

                            var text = $("#search-for").val();

                            //if (text != "") return;

                            if (!(typeof termElem === 'string') && !(termElem instanceof String)) {
                                $("#search-for").val(termElem.__data__.Term);
                            }
                            else {
                                $("#search-for").val(termElem);
                            }

                            term_on(termElem);
                        };

                     vis.term_off =
                        function(termElem) {

                            var text = $("#search-for").val();

                            //if (text != "") return;

                            $("#search-for").val("");

                            term_off(termElem);
                        };

                     vis.topic_click =
                        function ( newtopic_num) {

                            topic_num = newtopic_num;

                            $("#doc-list").html(spinner_html);

                            var text = $("#search-for").val();

                            get_docs(text);

                            topic_click(newtopic_num);
                        };

                     vis.topic_off =
                        function (topic) {

                            topic_num = topic;

                            topic_off(topic);
                        };

                     vis.state_url =
                        function() {
                            return state_url() +
                                "&selected_map=" + $("#map-select" ).val() +
                                "&n_topics=" + $("#ntopic-select" ).val();
                        };

                     vis.topic_on(topic_num);
                     vis.topic_click(topic_num);

                     var term = $("#search-for").val();

                     if (term !== "") {
                        vis.term_hover(term);
                        get_docs(term);
                     }

                     vis.state_save(true);

                 })(vis.term_on, vis.term_off, vis.topic_click, vis.topic_off, vis.state_url);
            }
        );
    }

    $("#map-select" )
      .change(
        function () {
            topic_num = 0;

            updateNTopicSelect();

            updateLDAVis();
        }
      );

    updateNTopicSelect();

    $("#ntopic-select" )
      .change(
        function () {
            topic_num = 0;

            updateLDAVis();
        }
      );

    function update_suggestions() {

        var text = $("#search-for").val();

        if($('#suggestions option').filter(
            function(){
                return this.value.toUpperCase() === text;
            }).length) return;

        $.get("suggestion/" + map_name + "/" + text).done(
            function(suggestions) {

                var tmp="";
                $.each(suggestions,
                   function(index, item){
                        tmp += `<option value="${item}">${item}</option>`
                    });

                $('#suggestions').html(tmp);
            }
        );
    }

    $("#search-for").change(update_suggestions);

    var url_params = new URLSearchParams(window.location.search);

    if (url_params.has("selected_map")) {
        $("#map-select" ).val(url_params.get("selected_map"));
    }

    if (url_params.has("n_topics")) {
        $("#ntopic-select" ).val(url_params.get("n_topics"));
    }

    if (url_params.has("term")) {
        $("#search-for" ).val(url_params.get("term"));
    }

    if (url_params.has("topic")) {
        topic_num = Number(url_params.get("topic"));
    }

    updateLDAVis();
};

$(document).ready(
    function() {
        $.get("topic_models").done(map_setup);
    }
);

})();