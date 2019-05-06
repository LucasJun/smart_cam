$("#ajax_status_table").ready(function(){
    $.get("ajax_status_table")
});

function isHumanDetect(){
    if($('#checkbox1').is(':checked')){
        alert("人类检测开启")
    }
    else{
        alert("人类检测关闭")
    }
}
function isMoveDetect(){
    if($('#checkbox2').is(':checked')){
        alert("移动检测开启")
    }
    else{
        alert("移动检测关闭")
    }
}
function isSmokeDetect(){
    if($('#checkbox3').is(':checked')){
        alert("烟雾检测开启")
    }
    else{
        alert("烟雾检测关闭")
    }
}
function isFireDetect(){
    if($('#checkbox4').is(':checked')){
        alert("火焰检测开启")
    }
    else{
        alert("火焰检测关闭")
    }
}