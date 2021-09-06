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

                (function(term_on, term_off, topic_click, topic_off) {

                    var topic_num = null;

                    function get_docs(text) {

                        if (topic_num == null) return;

                        if (text.length > 0) text = "/" + text;

                        $.get("topic_docs/" + map_name + "/" + topic_num + text,
                           function(topic_docs) {

                               $("#doc-list").html("");

                               for (i = 0; i < topic_docs.length; i++) {

                                   var url="https://digital.staatsbibliothek-berlin.de/werkansicht?PPN=PPN" + topic_docs[i].ppn;

                                   var item = `
                                       <li href="" class="list-group-item text-left">
                                           <a href="${url}" target="_blank" rel="noopener noreferrer"> ${topic_docs[i].title} </a>
                                           <a class="btn btn-info btn-sm ml-3"
                                               href="index.html?ppn=${topic_docs[i].ppn}&model_id=precomputed&el_model_id=precomputed&task=ner"
                                               target="_blank" rel="noopener noreferrer">NER+EL</a>
                                       </li>`;

                                   $("#doc-list").append(item);
                               }
                           });
                    }

                     $("#search-for").on('input',
                        function () {

                            var val = this.value;

                            if (val == "") {
                                term_off(null);
                                get_docs("");
                                return;
                            }

                            if($('#suggestions option').filter(
                                function(){
                                    return this.value.toUpperCase() === val.toUpperCase();
                                }).length)
                            {
                                term_on(this.value);
                                get_docs(this.value);
                            }
                        }
                     );

                     vis.term_on =
                        function(termElem) {

                            var text = $("#search-for").val();

                            if (text != "") return;

                            term_on(termElem);
                        };

                     vis.term_off =
                        function(termElem) {

                            var text = $("#search-for").val();

                            if (text != "") return;

                            term_off(termElem);
                        };

                     vis.topic_click =
                        function (newtopic, newtopic_num) {

                            topic_num = newtopic_num;

                            $("#doc-list").html(spinner_html);

                            var text = $("#search-for").val();

                            get_docs(text);

                            topic_click(newtopic, newtopic_num);
                        };

                     vis.topic_off =
                        function (circle) {

                            topic_off(circle);
                        };

                 })(vis.term_on, vis.term_off, vis.topic_click, vis.topic_off);
            }
        );
    }

    $("#map-select" )
      .change(
        function () {
            updateNTopicSelect();

            updateLDAVis();
        }
      );

    updateNTopicSelect();

    $("#ntopic-select" )
      .change(
        function () {
            updateLDAVis();
        }
      );

    $("#search-for").change(
        function() {

            var text = $("#search-for").val();

            if($('#suggestions option').filter(
                function(){
                    return this.value.toUpperCase() === text;
                }).length){
                return;
            }

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
    );

    updateLDAVis();
};

$(document).ready(
    function() {
        $.get("topic_models").done(map_setup);
    }
);

})();