function sbb_tools() {

    var that = null;
    var basic_auth = BasicAuth('#auth-area');
    var ned = null;

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

    function NED2(ner_url, parse_url, ned_url, result_element, result_entities_element, ner_result=null, ned_result={}) {

        ned = NED(ner_url, parse_url, ned_url, result_element, result_entities_element, ner_result, ned_result);

        function make_candidate(candidate) {

            var parts = candidate[0].split(/(?=[\.|\-|_])/);

            var tmp = parts.join("&shy;")

            return `
            <tr>
                <td class="my-auto">
                    <a href="https://de.wikipedia.org/wiki/${candidate[0]}" target="_blank" rel="noopener noreferrer">
                        <p class="text-wrap">${tmp}</p>
                    </a>
                </td>
                <td class="my-auto">
                    <a href="https://www.wikidata.org/wiki/${candidate[1]['wikidata']}" target="_blank" rel="noopener noreferrer">
                        ${candidate[1]['wikidata']}
                    </a>
                </td>
                <td class="my-auto">
                    ${Number(candidate[1]['proba_1']).toFixed(2)}
                </td>
                <td class="my-auto">
                    <div class="form">
                    <select class="form-select form-select-sm">
                      <option value="?">?</option>
                      <option value="+">+</option>
                      <option value="-">-</option>
                    </select>
                    </div>

                </td>
            </tr>
            `;
        }


        (function(makeResultList, getColor){

            ned.makeResultList =
                function(entities) {
                    $(ned.getResultEntitiesElement()).html("");

                    if (basic_auth.getUser() == null) {

                        makeResultList(entities);

                        return;
                    }

                    var entities_html = "";

                    entities.forEach(
                        function(candidate, index) {
                            entities_html += make_candidate(candidate);
                        }
                    );

                    entities_html =
                    `
                        <table class="table">
                          <thead>
                            <tr>
                              <th scope="col">Wiki&shy;pedia</th>
                              <th scope="col">Wiki&shy;data</th>
                              <th scope="col">Confi&shy;dence</th>
                              <th scope="col">Valid Answer?</th>
                            </tr>
                          </thead>
                          <tbody>
                            ${entities_html}
                          </tbody>
                        </table>
                    `;

                    $(ned.getResultEntitiesElement()).html(entities_html);
                }
        })(ned.makeResultList, ned.getColor);

        return ned;
    }

    function setup_precomputed(ppn) {
        var el_model = $('#el-model').val();
        var ner_url = "";
        var ned_url= el_model+"?return_full=0&priority=0";

        $.get("digisam-ner/" + ppn).done(
            function( ner_result ) {

                if (el_model == "precomputed") {
                    ned_url=null;

                    $.get( "digisam-el/" + ppn + "/0.15").done(
                        function( el_result ) {

                            var ned = NED2(ner_url, "ned/parse", ned_url, "#resultregion", "#entity-linking",
                                          ner_result, el_result);
                            ned.init("");

                            $("#legende").html(legende_html);

                        })
                    .fail(
                        function() {
                            console.log('Failed.');
                            $("#resultregion").html('Failed.');
                        });
                }
                else {
                    var ned = NED2(ner_url, "ned/parse", ned_url, "#resultregion", "#entity-linking",
                                  ner_result);

                    ned.init("");

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
