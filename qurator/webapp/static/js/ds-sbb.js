(function() {

var tools = sbb_tools();
var has_results = false;

$(document).ready(

    function() {

        $('#task').change(function(){ tools.task_select(); });
        $('#model_select').change(function(){ tools.model_select(); });
        $('#el_model_select').change(function(){ tools.el_model_select(); });

        $('#nerform').submit(
            function(e){
                e.preventDefault();

                update();
            }
        );

        function main_setup(data) {
            var tmp="";

             $.each(data,
                 function(index, item){

                     selected=""
                     if (item.default) {
                         selected = "selected"
                     }

                     tmp += '<option value="' + item.id + '" ' + selected + ' >' + item.name + '</option>'
                 });

              //$('#model_select option').first().after(tmp);

              var url_params = new URLSearchParams(window.location.search);

              var do_update=false;

              if (url_params.has('ppn')) {

                  var ppn = url_params.get('ppn')

                  $('#ppn').val(ppn);

                  do_update = true;
              }

              if (url_params.has('model_id')) {

                  var model_id = url_params.get('model_id')

                  $('#model').val(model_id);

                  do_update = true;
              }

              if (url_params.has('el_model_id')) {

                  var el_model_id = url_params.get('el_model_id')

                  $('#el-model').val(el_model_id);

                  do_update = true;
              }

              if (url_params.has('task')) {

                  var task = url_params.get('task')

                  $('#task').val(task);

                  do_update = true;
              }

              tools.task_select();

              if (do_update) update();
        }

        $.get( "ner/models")
            .done(
                function( data ) {
                    main_setup(data);
                }
                )
            .fail(
                function() {
                    main_setup([]);
                }
                );

        $.get( "ppnexamples")
            .done(
                function( data ) {
                    var tmp="";
                    $.each(data,
                        function(index, item){

                            tmp += '<option value="' + item.ppn + '">' + item.name + '</option>'
                        });
                    $('#ppnexamples').html(tmp);
                });
    });


function update() {

    if (has_results) {
        $(".inp").prop("disabled", false);
        $("#go-button").text("Go");
        has_results = false;
        tools.reset_view();

        return;
    }
    else {
        has_results = true;
        $(".inp").prop("disabled", true);
        $("#go-button").text("Clear");
    }

    var spinner_html =
        `<div class="d-flex justify-content-center">
            <div class="spinner-border align-center" role="status">
                <span class="sr-only">Loading...</span>
            </div>
         </div>`;

    var task = $('#task').val();
    var model_id = $('#model').val();
    var el_model_id = $('#el-model').val();
    var ppn = $('#ppn').val();

    var url_params = new URLSearchParams(window.location.search);

    url_params.set('ppn', ppn)
    url_params.set('model_id', model_id)
    url_params.set('el_model_id', el_model_id)
    url_params.set('task', task)

    window.history.replaceState({}, '', `${location.pathname}?${url_params}`);

    $("#resultregion").html(spinner_html);

    tools.do_task(task, model_id, ppn);
}

})();