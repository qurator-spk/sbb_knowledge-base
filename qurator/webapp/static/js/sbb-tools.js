function sbb_tools() {

    var that = null;
    var basic_auth = BasicAuth('#auth-area');
    var ned = null;
    var el_gt = { };

    (function(enable_login, enable_logout) {

        basic_auth.enable_logout =
            function() {
                enable_logout();

                if (ned == null) return;

                if(basic_auth.getUser() != null) {
                    $.get("annotate/" + ned.ppn).done(
                        function(data) {

                            el_gt = data;

                            ned.showNERText();
                        }
                    ).fail(
                        function(error) {
                            console.log(error);
                        }
                    );
                }
            }

        basic_auth.enable_login =
            function() {

                enable_login();

                if (ned==null) return;

                el_gt = {};

                ned.showNERText();
            };

    })(basic_auth.enable_login, basic_auth.enable_logout);

    var text_region_html =
        `<div class="card">
            <div class="card-header">
                Ergebnis:
            </div>
            <div class="card-block">
                <div id="textregion" style="overflow-y:scroll;height: 60vh;"></div>
            </div>
        </div>`;

    var legende_html =
         `<div class="card">
            <div class="card-header">
                <b>Entity-Recognition:</b>
            </div>
            <div class="card-body">
                <span>[<font color="red">Person</font>]</span>
                <span>[<font color="green">Ort</font>]</span>
                <span>[<font color="blue">Organisation</font>]</span>
                <span>[keine Named Entity]</div>
            </div>
        </div>`;

    var spinner_html =
        `<div class="d-flex justify-content-center mt-5">
            <div class="spinner-border align-center mt-5" role="status">
                <span class="sr-only">Loading...</span>
            </div>
         </div>`;

    function task_select() {

        var precomputed_option = `<option value="precomputed" id="precomputed-model">Precomputed</option>`;

        var task = $('#task').val();

        $('#model_select').hide();
        $('#el_model_select').hide();
        $('#precomputed-model').remove();

        if ((task == "ner") || (task == "bert-tokens")){

            $('#model_select').show();
        }

        if (task == "ner") {
            if ($('#model_select option').first().length > 0)
                $('#model_select option').first().before(precomputed_option);
            else
                $('#model').append(precomputed_option);
        }


        if (task == "ner") {
            $('#el_model_select').show();
        }

        that.reset_view();
    }

    function model_select() {
        if ($("#model").val()=="precomputed") {
            $("#el-model").val("precomputed");
        }
        else if (($("#el-model").val()=="precomputed") && ($("#model").val() != "precomputed")) {
            $("#el-model").val($("#el-model option:contains('German')").val());
        }
    }

    function el_model_select() {
        if ($("#el-model").val()=="precomputed") {
            $("#model").val("precomputed")
        }
    }

    function do_on_fulltext(ppn, func) {
        $.get( "digisam-fulltext/" + ppn)
            .done(function( data ) {
                func(data.text);
            })
            .fail(
                function() {
                    console.log('Failed.');
                    $("#resultregion").html('Failed.');
                });
    }

    function show_fulltext(input_text) {
        $("#resultregion").html(text_region_html);
        $("#textregion").html(input_text);
    }

    function show_tokenized_full_text(input_text) {

       $("#resultregion").html(spinner_html)

       var post_data = { "text" : input_text }

       $.ajax(
           {
           url:  "ner/tokenized",
           data: JSON.stringify(post_data),
           type: 'POST',
           contentType: "application/json",
           success:
               function( data ) {
                   text_html = ""
                   data.forEach(
                       function(sentence) {

                           text_html += JSON.stringify(sentence)

                           text_html += '<br/>'
                       }
                   )
                   $("#resultregion").html(text_region_html);
                   $("#textregion").html(text_html);
               }
           ,
           error:
               function(error) {
                   console.log(error);
               }
           });
    }

    function show_BERT_tokens(input_text) {

        var model_id = $('#model').val();
        $("#resultregion").html(spinner_html);

        var post_data = { "text" : input_text }

        $.ajax(
            {
            url:  "ner/ner-bert-tokens/" + model_id,
            data: JSON.stringify(post_data),
            type: 'POST',
            contentType: "application/json",
            success:
                function( data ) {
                    text_html = ""
                    data.forEach(
                        function(sentence) {
                            sentence.forEach(
                                function(part) {

                                     if (text_html != "") text_html += ' '

                                     text_html += part.token + "(" + part.prediction + ")"
                                })
                             text_html += '<br/>'
                        }
                    )
                    $("#resultregion").html(text_region_html)
                    $("#textregion").html(text_html)
                }
            ,
            error:
                function(error) {
                    console.log(error);
                }
            });
    }

    function setup_NED(input_text) {

        var model_id = $('#model').val();
        var el_model = $('#el-model').val();
        var ner_url = "ner/ner/" + model_id;
        var ned_url= el_model+"?return_full=0&priority=0";

        ned = NED2(ner_url, "ned/parse", ned_url,"#resultregion", "#entity-linking");

        ned.init(input_text);

        $("#legende").html(legende_html);
    }

    function NED2(ppn, ner_url, parse_url, ned_url, result_element, result_entities_element, ner_result=null, ned_result={}) {

        ned = NED(ner_url, parse_url, ned_url, result_element, result_entities_element, ner_result, ned_result);

        ned.ppn = ppn;

        function append_candidate(entity, candidate) {

            function insert_soft_hyphens(text) {
                var parts = text.split(/(?=[\.|\-|_])/);

                var tmp = parts.join("&shy;")

                return tmp;
            }

            function post_annotation(entity, candidate, label) {
                var post_data =
                    {
                        entity: entity,
                        candidate : candidate,
                        label : label
                    };

                $.ajax(
                    {
                        url:  `annotate/${ppn}`,
                        data: JSON.stringify(post_data),
                        type: 'POST',
                        contentType: "application/json",
                        success:
                            function() {
                            },
                        error:
                            function(error) {
                                console.log(error);
                            }
                    }
                );
            }

            function update_gt(entity, page_title, label) {
                if (label != "?") {
                    if (entity in el_gt) {
                        el_gt[entity][page_title] = label;
                    }
                    else {
                        el_gt[entity] = { 'length': 1};
                        el_gt[entity][page_title] = label;
                    }

                    $(".selected").addClass('with-gt');
                }
                else {
                    if (entity in el_gt) {
                        delete el_gt[entity][page_title];
                        el_gt[entity].length--;

                        if (el_gt[entity].length < 1) {
                            delete el_gt[entity];

                            $(".selected").removeClass('with-gt');
                        }
                    }
                }
            }

            var page_title = candidate[0];

            var page_title_vis = insert_soft_hyphens(page_title);

            var qid = candidate[1]['wikidata'];
            var wikidata_vis = insert_soft_hyphens(qid);

            var select_id = `select-gt-${entity}-${page_title}`.replace(/\W/g, '-');

            var wikipedia_html = "";
            var wikidata_html = "";
            var conf_html = "";

            var input_html =
                `
                <div class="form">
                    <select class="form-select form-select-sm" id="${select_id}">
                      <option value="?">?</option>
                      <option value="+">+</option>
                      <option value="-">-</option>
                    </select>
                </div>
                `;

            if ((page_title == "DO-NOT-LINK") || (page_title == "JOIN-LEFT")) {

                wikipedia_html = `<p class="text-wrap">${page_title_vis}</p>`;

                wikidata_html = `${wikidata_vis}`;
            }
            else if (page_title == "SUGGEST") {

                wikipedia_html = `<button class="btn btn-outline-secondary btn-sm" id="${select_id}-btn">Suggest</button>`;

                wikidata_html =
                    `
                    <input type="text" size=6/ id="${select_id}" disabled=true>
                    `;
                input_html = "";
            }
            else {

                wikipedia_html =
                `
                    <a href="https://de.wikipedia.org/wiki/${page_title}" target="_blank" rel="noopener noreferrer">
                        <p class="text-wrap">${page_title_vis}</p>
                    </a>
                `;

                wikidata_html =
                `
                    <a href="https://www.wikidata.org/wiki/${candidate[1]['wikidata']}" target="_blank" rel="noopener noreferrer">
                        ${wikidata_vis}
                    </a>
                `;

                conf_html = `${Number(candidate[1]['proba_1']).toFixed(2)}`;
            }

            var cand_html = `
            <tr>
                <td class="my-auto">
                    ${wikipedia_html}
                </td>
                <td class="my-auto">
                    ${wikidata_html}
                </td>
                <td class="my-auto">
                    ${conf_html}
                </td>
                <td class="my-auto">
                    ${input_html}
                </td>
            </tr>
            `;

            $("#entity-result-list").append(cand_html);

            if ((entity in el_gt) && (page_title in el_gt[entity])){
                    $(`#${select_id}`).val(el_gt[entity][page_title]);
            }

            if (page_title == "SUGGEST") {

                $(`#${select_id}-btn`).click(
                    function() {
                        $(`#${select_id}`).prop('disabled', false);
                    }
                );

                (function(entity, candidate) {
                    $(`#${select_id}`).change(
                        function() {
                            var qid = $(this).val();

                            if (qid.length < 1) {
                                update_gt(entity, page_title, "?");
                                post_annotation(entity, candidate, "?");
                            }
                            else {
                                update_gt(entity, page_title, qid);
                                post_annotation(entity, candidate, qid);
                            }

                            $(this).prop('disabled', true);
                        }
                    );
                }
                )(entity, candidate);
            }
            else {

                (function(entity, candidate) {
                    $(`#${select_id}`).change(
                        function() {
                            var label = $(this).val();

                            post_annotation(entity, candidate, label)

                            update_gt(entity, page_title, label);
                        }
                    );
                })(entity, candidate);
            }
        }

        (function(makeResultList, resultNotFound, getColor, getEntityItemClass){

            ned.makeResultList =
                function(entity, candidates) {
                    $(ned.getResultEntitiesElement()).html("");

                    if (basic_auth.getUser() == null) {

                        makeResultList(entity, candidates);

                        return;
                    }

                    var candidates_table =
                    `
                        <table class="table table-responsive">
                          <thead>
                            <tr>
                              <th scope="col">Wiki&shy;pedia</th>
                              <th scope="col">Wiki&shy;data</th>
                              <th scope="col">Confi&shy;dence</th>
                              <th scope="col">Valid Answer?</th>
                            </tr>
                          </thead>
                          <tbody id="entity-result-list">
                          </tbody>
                        </table>
                    `;

                    $(ned.getResultEntitiesElement()).html(candidates_table);

                    candidates.forEach(
                        function(candidate, index) {
                            append_candidate(entity, candidate);
                        }
                    );

                    append_candidate(entity,
                        ["DO-NOT-LINK",
                        {   "wikidata": "DO-NOT-LINK",
                            "proba_1": "nan",
                            "start_page": -1,
                            "stop_page": -1}]);

                    append_candidate(entity,
                        ["JOIN-LEFT",
                        {   "wikidata": "JOIN-LEFT",
                            "proba_1": "nan",
                            "start_page": -1,
                            "stop_page": -1}]);

                    append_candidate(entity,
                        ["SUGGEST",
                        {   "wikidata": "",
                            "proba_1": "nan",
                            "start_page": -1,
                            "stop_page": -1}]);
                };

            ned.resultNotFound =
                function (entity) {
                    if (basic_auth.getUser() == null) {
                        resultNotFound(entity);
                        return;
                    }

                    ned.makeResultList(entity, []);
                };

            ned.getColor =
                function(entity_text, entity_type) {
                    return getColor(entity_text, entity_type);
                };

            ned.getEntityItemClass =
                function(entity_text, entity_type) {

                    var entity = entity_text + "-" + entity_type;

                    if (entity in el_gt) {
                        return getEntityItemClass() + " with-gt";
                    }

                    return getEntityItemClass();
                };

        })(ned.makeResultList, ned.resultNotFound, ned.getColor, ned.getEntityItemClass);

        return ned;
    }

    function setup_precomputed(ppn) {
        var el_model = $('#el-model').val();
        var ner_url = "";
        var ned_url= el_model+"?return_full=0&priority=0";

        function make_NED(ner_result, el_result) {
            var ned = NED2(ppn, ner_url, "ned/parse", ned_url, "#resultregion", "#entity-linking", ner_result, el_result);
            ned.init("");
        }

        $.get("digisam-ner/" + ppn).done(
            function( ner_result ) {

                if (el_model == "precomputed") {
                    ned_url=null;

                    $.get( "digisam-el/" + ppn + "/0.15").done(
                        function( el_result ) {

                            if(basic_auth.getUser() != null) {
                                $.get("annotate/" + ppn).done(
                                    function(data) {

                                        el_gt = data;

                                        make_NED(ner_result, el_result);
                                    }
                                ).fail(function() { make_NED(ner_result, el_result); });
                            }
                            else {
                                make_NED(ner_result, el_result);
                            }

                            $("#legende").html(legende_html);

                        })
                    .fail(
                        function() {
                            console.log('Failed.');
                            $("#resultregion").html('Failed.');
                        });
                }
                else {
                    make_NED(ner_result, {});

                    $("#legende").html(legende_html);
                }
            }
        ).fail(
            function() {
                console.log('Failed.');
                $("#resultregion").html('Failed.');
            }
        );
    }

    that = {

        reset_view:
            function () {
                $("#resultregion").html("");
                $("#legende").html("");
                $("#entity-linking").html("");

                el_gt = {};
                ned = null;
            },
        init:
            function (task, ppn) {

                basic_auth.getUser();

                $("#resultregion").html(spinner_html);

                var model_id = $('#model').val();

                $("#legende").html("");

                $("#resultregion").html(spinner_html);

                if (task == "fulltext") {

                    do_on_fulltext(ppn, show_fulltext);
                }
                else if (task == "tokenize") {

                    do_on_fulltext(ppn, show_tokenized_full_text);
                }
                else if (task == "ner") {

                    if (model_id == "precomputed") {
                        setup_precomputed(ppn);
                    }
                    else {
                        do_on_fulltext(ppn, setup_NED);
                    }
                 }
                 else if (task == "bert-tokens") {

                    do_on_fulltext(ppn, show_BERT_tokens);
                 }
            }
    };

    task_select();
    model_select();

    $('#task').change(function(){ task_select(); });
    $('#model_select').change(function(){ model_select(); });
    $('#el_model_select').change(function(){ el_model_select(); });

    //$('select').selectpicker();

    return that;
}
