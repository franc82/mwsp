function updateAcq(arrGuests) {
    var objNames = {};
    jQuery(arrGuests).each(function(idx, elt) {
      objNames[elt.id] = elt.name;
    });
    jQuery(arrGuests).each(function(idx, elt){
      var arrFriendsIDs = elt.friends || [];
      var arrFriends = [];

      for (var i=0,l=arrFriendsIDs.length; i < l; ++i){
          arrFriends.push(objNames[arrFriendsIDs[i]]);
      }

      jQuery('#'+ elt.id + ' .ai-relation').text(arrFriends.join(', ') || '(None)');
    });
}

jQuery(document).ready(function (){
    if (jQuery('.ai-about-section-content-card').length > 0){
        jQuery('.ai-about-section-content-card').each(function( index ) {
            var $this = jQuery(this);
            var height = $this.find('.ai-about-section-card-content').height();
            $this.find('.ai-about-section-content-card-icon').css('line-height', height+'px');
        });
    }

    if (jQuery('.ai-add-guest-custom-file-upload').length > 0){
        jQuery(document).on('click', '.ai-add-guest-custom-file-upload', function (evt){
            evt.preventDefault();
            jQuery('#ai-add-guest-upload-csv').click();
        });
        jQuery('#ai-add-guest-upload-csv').change(function(e){
            e.preventDefault();
            var fileName = e.target.files[0].name;
            jQuery('.ai-add-guest-custom-file-upload').find('span').text('Selected '+fileName);
        });
    }

    jQuery(document).on('click', '.ai-modal-add-guest , .ai-modal-update-guest', function(evt){
        evt.preventDefault();
        jQuery('#ai-add-guest-modal').modal('hide');
        jQuery('#ai-guest-detail-acquaintance').modal('hide');
        jQuery('.ai-preloader').hide();
    });

    if (jQuery('.ai-guest-list').length > 0) {
        jQuery(document).on('click', '.ai-guest-list .ai-actions i.fa-pencil-square-o', function(evt){
            evt.preventDefault();
            var $this = jQuery(this),
            $parent = $this.closest('tr'),
            $Sname = $parent.find('.ai-name').text();
            jQuery.getJSON('/guest/' + $parent.prop('id'), function(arrGuests) {
                var sTickboxMarkup = '';
                jQuery('#ai-guest-detail-modal #ai-modal-guest-list').html('');
                jQuery('.ai-selected-guests').children('div').remove();
                jQuery('#ai-guest-detail-modal .modal-body .heading h2 span').text(arrGuests.guest.name);
                var sMarkup = '<input type="hidden" id="guestid" name="guestid"'+ ' value=' + ($parent.prop('id')) + '>';
                jQuery(arrGuests.guestlist).each(function(i,elt){
                    sMarkup += '<div class="checkbox">';
                    sMarkup += '<label style="font-size: 14px;">';
                    sMarkup += '<input id="guest-id-'+(elt.id)+'" type="checkbox"' + (jQuery.inArray(elt.id, arrGuests.guest.friends || []) > -1 ? ' checked=true' : '') + 'value="'+(elt.name)+'">'+(elt.name);
                    sMarkup += '</label>';
                    sMarkup += '</div>';

                    if (jQuery.inArray(elt.id, arrGuests.guest.friends || []) > -1) {
                        // add an element in the tick box section
                        sTickboxMarkup += '<div class="ai-selected-guest-pill">';
                        sTickboxMarkup += ' <span>' + (elt.name) + '</span>';
                        sTickboxMarkup += ' <i class="fa fa-times" id="guest-id-' + (elt.id) + '">';
                        sTickboxMarkup += '</i></div>';
                    }
                });

                // update guest name and acquintance
                jQuery('#ai-guest-name').val(arrGuests.guest.name);
                jQuery('#ai-guest-acquaintance option').each(function() {
                    this.selected = (jQuery(this).val().toUpperCase() == arrGuests.guest.acq.toUpperCase());
                });

                jQuery('#ai-guest-detail-modal #ai-modal-guest-list').append(sMarkup);
                jQuery('.ai-selected-guests').append(sTickboxMarkup);
            });

            jQuery(document).one('click', '.ai-modal-update-guest', function(evt){
                evt.preventDefault();
                // getting the action to perform
                var classes = jQuery(evt.target).attr('class').split(/\s+/);
                var arrAction = classes[classes.length - 1].split('-');

                // last elt is either ok or cancel
                if (arrAction[arrAction.length - 1] == 'ok') {
                    // elt updating, grabbing the records to be sent
                    var arrGuestIDs = [];
                    jQuery('#ai-modal-guest-list input[type=checkbox]:checked').each(function(){
                        var arrCurrentID = this.id.split('-');
                        arrGuestIDs.push(arrCurrentID[arrCurrentID.length - 1]);
                    });
                    var objRecord = {
                      'guestid' : jQuery('#guestid').val(),
                      'name' : jQuery('#ai-guest-name').val(),
                      'acq' : jQuery('#ai-guest-acquaintance').val(),
                      'friends' : arrGuestIDs.join(',')
                     }

                    jQuery.post('/guest/'+ objRecord.guestid, objRecord, function(response) {
                       // if successful then update the relevant row in the table
                       var arrGuests = [];
                       jQuery(arrGuestIDs).each(function(){
                          arrGuests.push(jQuery('#' + this + ' .ai-name').text());
                       });

                       jQuery('#' + objRecord.guestid  + ' .ai-name').text(objRecord.name);
                       jQuery('#' + objRecord.guestid  + ' .ai-acquaintance').text(objRecord.acq || '(None)');
                       var objNames = {};
                       jQuery(response.guestslist).each(function(idx, elt) {
                          objNames[elt.id] = elt.name;
                       });

                       // updating the relationship and acq <TD>
                       jQuery(response.guestslist).each(function(idx, elt) {
                          var arrFriendsIDs = elt.friends || [];
                          var arrFriends = [];

                          for (var i=0, l=arrFriendsIDs.length; i < l; ++i){
                              arrFriends.push(objNames[arrFriendsIDs[i]]);
                          }

                          jQuery('#'+ elt.id + ' .ai-relation').text(arrFriends.join(', ') || '(None)');
                          
                          // update the acq node for other nodes
                          if (elt.id != objRecord.guestid) {
                            jQuery('#'+ elt.id + ' .ai-acquaintance').text(elt.acq || '(None)');
                          }
                       });

                       jQuery('#ai-guest-detail-modal').modal('hide');
                    }, 'json');
                } else if (arrAction[arrAction.length - 1] == 'cancel') {
                    // deleting item
                    if (confirm('Are you sure you want to delete this guest?')) {
                        var guestid = jQuery('#guestid').val();
                        jQuery.post('/delete/'+ guestid, function(response){
                            console.log('number of remaining guests = '+ response.numguests);
                            // remove the guest from the table
                            jQuery('tr#'+guestid).remove();
                            jQuery('#ai-guest-detail-modal').modal('hide');

                            // updating the acq
                            updateAcq(response.guests);
                        }, 'json');
                    }
                }
            });
        });

        jQuery(document).on('click', '.ai-guest-list .ai-actions i.fa-trash', function(evt){
            evt.preventDefault();
            if (confirm("Are you sure you want to delete this guests?")) {
                var $this = jQuery(this),
                $parent = $this.closest('tr'),
                $Sname = $parent.find('.ai-name').text();
                jQuery.post('/delete/'+ $parent.prop('id'), function(response){
                    $parent.addClass('ai-delete').fadeOut('slow', function(){
                        $parent.remove();
                    });

                    // updating the number of guest node
                    jQuery('.ai-detail-card:first h5').text(function(i, oldMarkup) {
                      if (typeof response.numguests != 'undefined') {
                        return response.numguests;
                      } else {
                        return oldMarkup;
                      }
                    });

                    // updating the relationship between the guests as it may have changed as a result
                    // of the deletion of a guest
                    updateAcq(response.guests);
                }, 'json');
            }
        });

        jQuery(document).on('click', '.ai-guest-list .ai-name', function(evt){
            evt.preventDefault();
            var $this = jQuery(this),
            $parent = $this.closest('tr'),
            $Sname = $parent.find('.ai-name').text();
            $relation = $parent.find('.ai-relation').text();
            $acquaintance = $parent.find('.ai-acquaintance').text();
            jQuery('#ai-guest-detail-acquaintance .heading .ai-modal-acquaintance span').text($acquaintance);
            jQuery('#ai-guest-detail-acquaintance .heading .ai-modal-name span').text($Sname);
            jQuery('#ai-guest-detail-acquaintance .heading .ai-modal-relation span').text($relation);
            jQuery('#ai-guest-detail-acquaintance .ai-modal-content .ai-modal-content-append').html('');
            jQuery('.ai-guest-list tbody .ai-name').each(function() {
                var $name = jQuery(this).text();
                if ($name != $Sname){
                    var $output = null;
                    $output = '<div class="checkbox"><label><input type="checkbox" value="'+$name+'">'+$name+'</label></div>';
                    jQuery('#ai-guest-detail-acquaintance .ai-modal-content .ai-modal-content-append').append($output);
                }
            });
        });
    }

    if (jQuery('.ai-ppl-table').length > 0){
        jQuery(document).on('click', '.ai-ppl-table', function(){
            var $this = jQuery(this),
                tableno = $this.find('label').text();
            jQuery('#ai-table-sitter-list .heading h2 span').text(tableno);
        });
    }

    jQuery(document).on('click', '#ai-modal-guest-list .checkbox input[type=checkbox]', function(evt){
        //evt.preventDefault();
        var $this = jQuery(this),
            name = $this.val(),
            target_id = $this.attr('id'),
            output = '<div class="ai-selected-guest-pill"><span>'+name+'</span> <i class="fa fa-times" id="'+target_id+'"></i></div>';
        if ($this.is(':checked')) {
            jQuery('.ai-selected-guests').append(output);
        } else {
            jQuery('.ai-selected-guests').find('#'+target_id).closest('.ai-selected-guest-pill').remove();
        }
    });

    jQuery(document).on('click', '.ai-selected-guest-pill i', function(evt){
        evt.preventDefault();
        var $this = jQuery(this),
            target_id = $this.attr('id');
        jQuery('#ai-modal-guest-list .checkbox input[type=checkbox]#'+target_id).prop('checked', false);
        $this.parent().remove();
    });

    jQuery(document).on('click', '#paylink', function(evt){
        evt.preventDefault();
        var stripe = Stripe('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');
        stripe.redirectToCheckout({
          // Make the id field from the Checkout Session creation API response
          // available to this file, so you can provide it as parameter here
          // instead of the {{CHECKOUT_SESSION_ID}} placeholder.
          sessionId: jQuery('#stripesessionid').val()
        }).then(function (result) {
          // If `redirectToCheckout` fails due to a browser or network
          // error, display the localized error message to your customer
          // using `result.error.message`.
          alert('failed redirect: '+ result.error.message);
        });
    });
});


function updateGuest(evt) {
  evt.preventDefault();
  var objRecord = {
      'guestid' : 1,
      'name' : 'John Doe',
      'acq' : 'Bride',
      'friends' : [5,8,10].join(',')
  }

  jQuery.post('/guest/'+ objRecord.guestid, objRecord, function(response) {
   jQuery('#ai-guest-detail-modal').modal('toggle');
  }, 'json');
}
