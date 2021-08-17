function sbb_tools() {

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

        reset_view();
    }

    function reset_view() {
        $("#resultregion").html("");
        $("#legende").html("");
        $("#entity-linking").html("");
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

    function do_task(task, model_id, ppn) {

        var text_region_html =
            `<div class="card">
                <div class="card-header">
                    Ergebnis:
                </div>
                <div class="card-block">
                    <div id="textregion" style="overflow-y:scroll;height: 45vh;"></div>
                </div>
            </div>`;

        var legende_html =
             `<div class="card">
                <div class="card-header">
                    <b>Entity-Recognition:</b>
                </div>
                <div class="card-body">
                    <div class="ml-2" >[<font color="red">Person</font>]</div>
                    <div class="ml-2" >[<font color="green">Ort</font>]</div>
                    <div class="ml-2" >[<font color="blue">Organisation</font>]</div>
                    <div class="ml-2" >[keine Named Entity]</div>
                </div>
            </div>`;

        var spinner_html =
            `<div class="d-flex justify-content-center mt-5">
                <div class="spinner-border align-center mt-5" role="status">
                    <span class="sr-only">Loading...</span>
                </div>
             </div>`;

        $("#legende").html("");

        $("#resultregion").html(spinner_html);

        if (task == "fulltext") {

            do_on_fulltext(ppn,
                function(input_text) {
                    $("#resultregion").html(text_region_html);
                    $("#textregion").html(input_text);
                 });
        }
        else if (task == "tokenize") {

            do_on_fulltext(ppn,
                function(input_text) {

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
                 });
        }
        else if (task == "ner") {

            var el_model = $('#el-model').val();

            var ner_url = "ner/ner/" + model_id;
            var ned_url= el_model+"?return_full=0&priority=0";

            if (model_id == "precomputed") {

                ner_url="";

                var ppn = $('#ppn').val();

                $.get( "digisam-ner/" + ppn)
                    .done(function( ner_result ) {

                        if (el_model == "precomputed") {
                            ned_url=null;

                            $.get( "digisam-el/" + ppn + "/0.15").done(
                                function( el_result ) {

                                    var ned = NED(ner_url, "ned/parse", ned_url, "#resultregion", "#entity-linking",
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
                            var ned = NED(ner_url, "ned/parse", ned_url, "#resultregion", "#entity-linking",
                                          ner_result);

                            ned.init("");

                            $("#legende").html(legende_html);
                        }
                    })
                    .fail(
                        function() {
                            console.log('Failed.');
                            $("#resultregion").html('Failed.');
                        });
            }
            else {
                do_on_fulltext(ppn,
                    function(input_text) {

                        var ned = NED(ner_url, "ned/parse",
                                      el_model+"?return_full=0&priority=0","#resultregion", "#entity-linking");

                        ned.init(input_text);

                        $("#legende").html(legende_html);
                     });
            }
         }
         else if (task == "bert-tokens") {

            do_on_fulltext(ppn,
                function(input_text) {

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
                });
         }
    }

    task_select();
    model_select();

    return { 'do_task': do_task, 'reset_view': reset_view, 'task_select': task_select, 'model_select': model_select,
     'el_model_select': el_model_select}
}