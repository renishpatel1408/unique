// @odoo-module ignore

/**
 * Runs only when DOM is ready.
 */
$(function () {
    console.log("✅ Partner Portal jQuery loaded successfully (ignore mode)");

    const csrf_token = $('input[name="csrf_token"]').val();

    // Handle radio change
    $('input[name="action_selection"]').change(function () {
        const selected = $(this).val();
        $('#approve_btn, #block_btn').addClass('d-none');

        if (selected === 'approve') {
            $('#approve_btn').removeClass('d-none');
        } else if (selected === 'block') {
            $('#block_btn').removeClass('d-none');
        }
    });

    // Approve button
    $('#approve_btn').click(function () {
        const Partner_id = $(this).data('id');
        const token = $(this).data('token');
        $.post(`/partner/approve/${token}`, { csrf_token , token}, function (result) {
            if (result === 'true' || result === true) {
                location.reload();
            }
        });
    });

    $('#block_btn').click(function () {
        $(this).addClass('d-none');
        const Partner_id = $(this).data('id');
        const token = $(this).data('token');
        $.post(`/partner/block/${token}`, { csrf_token, token }, function (result) {
            if (result === 'true' || result === true) {
                location.reload();
            }
        });
    });   
});
