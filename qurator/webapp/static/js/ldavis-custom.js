(function() {

function map_setup(maps) {
    var map_names = new Set();
    var n_topics = {}
    var map_data = {}

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

                (function(term_on, term_off) {
                     $("#search-for").on('input',
                        function () {

                            var val = this.value;

                            if (val == "") {
                                term_off(null);
                                return;
                            }

                            if($('#suggestions option').filter(
                                function(){
                                    return this.value.toUpperCase() === val.toUpperCase();
                                }).length)
                            {
                                term_on(this.value);
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

                 })(vis.term_on, vis.term_off);
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