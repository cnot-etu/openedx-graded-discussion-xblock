/* Javascript for GradedDiscussionXBlock. */
function GradedDiscussionXBlock(runtime, element) {

    function renderContributions(data){
        $(".list-contributions").empty();

        data.forEach(function(entry) {
            if ( entry.kind === "thread"){
                $(".list-contributions").append(createThreadElement(entry.contribution, entry.created_at));
            } else {
                $(".list-contributions").append(createCommentElement(entry.contribution, entry.parent, entry.created_at));
            }
        });
        updateDateTime();
    };


    function createThreadElement(contribution, createdAt){
        var element = $("<li></li>");
        var div = $('<div class="thread-contribution"></div>');
        var contribution = $('<p>'+contribution+'</p>');
        var date = $('<span class="date-time" value="'+createdAt+'"></span>');

        contribution.appendTo(div);
        date.appendTo(div);
        div.appendTo(element);

        return element

    }

    function createCommentElement(contribution, parent, createdAt){
        var element = $("<li></li>");
        var div = $('<div class="comment-contribution"></div>');
        var contribution = $('<p>'+contribution+'</p>');
        var parent = $('<span class="parent-contribution">'+parent.name+' by '+parent.author+'</span>');
        var date = $('<span class="date-time" value="'+createdAt+'"></span>');

        contribution.appendTo(div);
        parent.appendTo(div);
        date.appendTo(div);
        div.appendTo(element);

        return element

    }

    function updateDateTime(){
        $(".contributions-section .date-time").each(function() {
            var date = new Date($(this).attr("value"));
            $(this).text(date.toLocaleString());
        });
    }

    $(function ($) {
        /* Here's where you'd do things on page load. */
    });

    var reloadPage = runtime.handlerUrl(element, "refresh_data");

    updateDateTime();

    $(".reload-button").click(function(){
        $.ajax({
            type: "GET",
            url: reloadPage,
            success: renderContributions
        });
    })
}
