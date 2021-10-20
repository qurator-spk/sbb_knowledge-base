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

        var old_n_topics = $("#ntopic-select").val();

        $("#ntopic-select").html("");
        n_topics[selected_map].forEach(
            function(n_top, index) {

                var html = `<option value=${n_top}>${n_top}</option>`;

                $("#ntopic-select").append($(html));
            }
        );

        if (map_data[[selected_map,old_n_topics]] !== undefined) $("#ntopic-select").val(old_n_topics);
    }

    var vis = null;
    var map_name = null;

    var request_counter=0;
    var topic_docs = [];
    var meta_info = {};

    function make_doc_list(new_topic_docs, new_meta_info=null) {

        request_counter += 1;

        topic_docs = new_topic_docs;

        (function(counter_at_request) {

            var trigger_counter = 0;
            var search_id = $("#search-for").val().match(/Q[0-9]+/);

            if (new_meta_info === null) $("#doc-list").html(spinner_html);

            function triggerNextDoc () {
                trigger_counter += 1;

                if (topic_docs.length <= 0) return;
                if (counter_at_request < request_counter) return;
                if (trigger_counter > 50) return;

                var next_doc = topic_docs.shift();

                var url="https://digital.staatsbibliothek-berlin.de/werkansicht?PPN=PPN" + next_doc;

                var meta = meta_info[next_doc];

                if (meta === undefined) triggerNextDoc();

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
                            if (counter_at_request < request_counter) return;

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
                            triggerNextDoc();
                        }
                    );
                })("PPN" + next_doc);
            }

            if (new_meta_info !== null) {
                meta_info = new_meta_info;

                triggerNextDoc();
            }
            else {
                let post_data = { "ppns" : topic_docs };

                $.ajax({
                        url:  "meta_data",
                        data: JSON.stringify(post_data),
                        type: 'POST',
                        contentType: "application/json",
                        success:
                            function(result) {

                                if (counter_at_request < request_counter) return;

                                $("#doc-list").html("");

                                meta_info = result;

                                triggerNextDoc();
                            },
                        error:
                            function(error) {
                                $("#doc-list").html("Not available.");
                            }
                    }
                );
            }

        })(request_counter);
    }

    var topic_num = 0;

    function get_docs(order_by) {

        if (topic_num == 0) return;

        if (order_by.length > 0) order_by = "/" + order_by;

        $.get("topic_docs/" + map_name + "/" + topic_num + order_by,
            function(topic_docs) {
                make_doc_list(topic_docs);
            });
    }

    var search_term = "";
    var suggestions_html = "";
    var last_search="";

    function update_suggestions(success) {

        search_term = $("#search-for").val();

        if($('#suggestions option').filter(
            function(){
                return this.value.toUpperCase() === search_term;
            }).length) return;

        $.get("suggestion/" + map_name + "/" + search_term).done(
            function(suggestions) {

                suggestions_html="";
                $.each(suggestions,
                   function(index, item){
                        suggestions_html += `<option value="${item}">${item}</option>`
                    });

                $('#suggestions').html(suggestions_html);
                $('#suggestions').focus();

                success();
            }
        );
    }

    function updateLDAVis() {

        request_counter += 1;

        $("#chart").html("");
        $("#doc-list").html("");
        $("svg").remove();
        $("#mds").html(spinner_html);
        $("#mds-heading").text("");
        $("#mds-input").addClass("d-none");

        var selected_map = $("#map-select" ).val();

        var n_topics = $("#ntopic-select" ).val();
        map_name = map_data[[selected_map,n_topics]]

        var docs_timeout=null;

        $.get("topic_models/" + map_name,
            function(data) {

                $("#mds").html("");
                $("#mds-input").removeClass("d-none");

                vis = LDAvis(data);

                (function(term_on, term_off, term_click, topic_click, topic_off, state_url) {

                    function update_on_search_input () {

                        search_term = $("#search-for").val();

                        if (search_term == "") {
                            last_search=search_term;
                            term_click("");
                            term_off("");
                            get_docs("");
                            vis.state_save(true);
                            return;
                        }

                        update_suggestions(
                            function() {

                                if ($('#suggestions option').filter(
                                    function(){
                                        return this.value.toUpperCase() === search_term.toUpperCase();
                                    }).length)
                                {
                                    last_search=search_term;
                                    term_click(search_term);
                                    term_on(search_term);

                                    clearTimeout(docs_timeout);

                                    docs_timeout = setTimeout(
                                        function() {
                                            get_docs(search_term);
                                        }, 2000);

                                    vis.state_save(true);
                                }
                            }
                        );
                    }

                     $("#search-for").on('input', update_on_search_input);

                     vis.term_on =
                        function(term) {

                            //console.log("term_on");

                            search_term = $("#search-for").val();

                            $("#search-for").val(term);

                            if (($('#suggestions option').filter(
                                function(){
                                    return this.value.toUpperCase() === search_term.toUpperCase();
                                }).length) && (term !== search_term)) {

                                term_off(search_term);
                            }

                            term_on(term);
                        };

                     vis.term_off =
                        function(term) {

                            $("#search-for").val(search_term);
                            $("#suggestions").html(suggestions_html);

                            term_off(term);

                            if($('#suggestions option').filter(
                                function(){
                                    return this.value.toUpperCase() === search_term.toUpperCase();
                                }).length)
                            {
                                clearTimeout(docs_timeout);

                                docs_timeout = setTimeout(
                                    function() {
                                        get_docs(search_term);
                                    }, 2000);

                                term_on(search_term);
                            }
                            else if (search_term === "") {

                                clearTimeout(docs_timeout);

                                docs_timeout = setTimeout(
                                    function() {
                                        get_docs("");
                                    }, 2000);
                            }
                         };

                     vis.term_click =
                        function(term) {

                            update_on_search_input();

                            vis.state_save(true);
                        };

                     vis.topic_click =
                        function ( newtopic_num) {

                            topic_num = newtopic_num;

                            var text = $("#search-for").val();

                            topic_click(newtopic_num);

                            get_docs(text);
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

                 })(vis.term_on, vis.term_off, vis.term_click, vis.topic_click, vis.topic_off, vis.state_url);

                 var term = $("#search-for").val();

                 if (term === "") {
                    vis.topic_click(topic_num);
                    get_docs("");
                 }
                 else {
                     update_suggestions(
                        function(){
                            vis.topic_click(topic_num);
                            last_search = term;
                            vis.term_click(term);
                            vis.term_on(term);
                            get_docs(term);
                        }
                     );
                 }

                 vis.state_save(true);
            }
        ).
        fail(
            function(error) {

                var err_msg = `
                    <div class="alert alert-danger alert-dismissible fade show">
                        Map not available.
                    </div>
                `;

                $("#mds").html(err_msg);
                console.log(error);
            });
    }

    var suggestion_timeout=null;

    $("#map-select" )
      .change(
        function () {
            topic_num = 0;
            last_search = "";
            $("#search-for").val("")

            if (suggestion_timeout !== null) clearTimeout(suggestion_timeout);

            updateNTopicSelect();

            updateLDAVis();
        }
      );

    updateNTopicSelect();

    $("#ntopic-select" )
      .change(
        function () {
            topic_num = 0;
            last_search = "";
            $("#search-for").val("")

            if (suggestion_timeout !== null) clearTimeout(suggestion_timeout);

            updateLDAVis();
        }
      );

    $("#search-for").on("keyup",
        function(e) {

            if (suggestion_timeout !== null) clearTimeout(suggestion_timeout);

            if ($("#search-for").val() == last_search) return;

            last_search = $("#search-for").val();

            suggestion_timeout = setTimeout(
                function() {
                    update_suggestions(function(){});
                }, 500);
        }
    );

    var scroll_timeout=null;

    $("#doc-list" ).scroll(
        function() {
            if (scroll_timeout !== null) clearTimeout(scroll_timeout);

            scroll_timeout = setTimeout(
                function() {
                    make_doc_list(topic_docs, meta_info); // load next N-elements
                }, 1000);
        }
    );

    var url_params = new URLSearchParams(window.location.search);

    if (url_params.has("selected_map")) {
        $("#map-select" ).val(url_params.get("selected_map"));

        updateNTopicSelect();
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